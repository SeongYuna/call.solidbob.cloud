# Requirement: F-3, SEC-1
"""BriefingFactsPort 의 PostgreSQL 구현 — 읽기만 한다. 담긴 글자는 마스킹본에서 나온 것뿐이다(SEC-1).

**`compliance_flag` 는 읽지 않는다** — 상담원 기록이지 고객 정보가 아니다(`decisions/220` 1절).
절차 판정은 같은 절차에 여러 번 쌓이므로 **절차별 마지막 판정**만 본다.
"""

from __future__ import annotations

from collections import defaultdict

from hub.app.dtos.customer_briefing_dto import BriefingFacts, PriorCall
from hub.app.ports.output.briefing_facts_port import BriefingFactsPort

from .connection import ConnectionFactory

MAX_PRIOR_CALLS = 5

_CURRENT = 'SELECT "customer_id", "started_at" FROM "call" WHERE "call_id" = %s'
_PRIOR = """
SELECT "call_id", "started_at", "inquiry_type", "summary_text", "summary_confirmed_at"
FROM "call"
WHERE "customer_id" = %s AND "call_id" <> %s AND "started_at" < %s
ORDER BY "started_at" DESC, "call_id" DESC LIMIT %s
"""
_FOLLOW_UPS = """
SELECT "call_id", "action_text" FROM "follow_up_action"
WHERE "call_id" = ANY(%s) AND "status" IN ('draft', 'confirmed') ORDER BY "created_at", "id"
"""
_LATEST_CLOSURES = """
SELECT DISTINCT ON ("call_id", "procedure") "call_id", "procedure", "verdict" FROM "closure"
WHERE "call_id" = ANY(%s) ORDER BY "call_id", "procedure", "decided_at" DESC, "closure_id" DESC
"""
_CALL_GUARD = 'SELECT DISTINCT "call_id", "category" FROM "call_guard_flag" WHERE "call_id" = ANY(%s) ORDER BY "call_id", "category"'
_BLACKLISTED = """
SELECT EXISTS (SELECT 1 FROM "blacklist_entry"
               WHERE "customer_ref" = %s AND "released_at" IS NULL AND "expires_at" > now())
"""


class PostgresBriefingFactsRepository(BriefingFactsPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def collect(self, call_id: str) -> BriefingFacts | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_CURRENT, (call_id,))
                current = await cur.fetchone()
                if current is None:
                    return None
                customer_id, started_at = current
                if customer_id is None:
                    return BriefingFacts(call_id=call_id, customer_identified=False)
                await cur.execute(_PRIOR, (customer_id, call_id, started_at, MAX_PRIOR_CALLS))
                prior_rows = await cur.fetchall()
                ids = [r[0] for r in prior_rows]
                follow_ups, closures, guards = [], [], []
                if ids:
                    await cur.execute(_FOLLOW_UPS, (ids,))
                    follow_ups = await cur.fetchall()
                    await cur.execute(_LATEST_CLOSURES, (ids,))
                    closures = await cur.fetchall()
                    await cur.execute(_CALL_GUARD, (ids,))
                    guards = await cur.fetchall()
                await cur.execute(_BLACKLISTED, (customer_id,))
                (blacklisted,) = await cur.fetchone()

        fu: dict[str, list[str]] = defaultdict(list)
        for cid, text in follow_ups:
            fu[cid].append(text)
        incomplete: dict[str, list[str]] = defaultdict(list)
        for cid, procedure, verdict in closures:
            if verdict == "incomplete":
                incomplete[cid].append(procedure)
        cg: dict[str, list[str]] = defaultdict(list)
        for cid, category in guards:
            cg[cid].append(category)
        prior = tuple(
            PriorCall(call_id=cid, started_at=at, inquiry_type=itype, summary_text=summary,
                      summary_confirmed=confirmed_at is not None,
                      open_follow_ups=tuple(fu[cid]), incomplete_procedures=tuple(incomplete[cid]),
                      call_guard_categories=tuple(cg[cid]))
            for cid, at, itype, summary, confirmed_at in prior_rows
        )
        return BriefingFacts(call_id=call_id, customer_identified=True, prior_calls=prior, blacklisted=bool(blacklisted))
