# Requirement: J-5
"""AgentRoutingPort 의 PostgreSQL 구현 — 판정 재료를 모아 **도메인 규칙**에 맡기고 결과를 `routing_log` 에 남긴다(`decisions/313`).

- 블랙리스트 여부: 통화의 `customer_id` 로 **적용 중** 등록(`released_at IS NULL AND expires_at > now`)이 있는가
- 근속: `agent.hired_on` 에서 지금까지(365.25일 = 1년). 입사일이 없으면 0년 — 베테랑으로 치지 않는다
- 후보: 부르는 쪽이 준 ID 중 `agent` 에 있는 것만. 없는 ID 는 `unknown_candidates` 로 돌려준다(지어내지 않는다)
- 기준: `app_setting.veteran_years`, 없으면 도메인 기본값

**판정은 이 파일에 없다** — `route()` 가 한다. 이 어댑터에는 «근속이 몇 년이면» 같은 if 가 없다(절대 원칙 9).
**`call.agent_id` 는 건드리지 않는다** — 판정일 뿐 실제로 받은 상담사가 아니다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hub.adapter.outbound.postgres.connection import ConnectionFactory
from hub.app.dtos.blacklist_dto import AgentProfile
from hub.app.dtos.routing_decision_dto import RoutedCall
from hub.app.ports.output.agent_routing_port import AgentRoutingPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

from ...domain.services.routing import route
from .postgres_routing_setting_repository import read_veteran_years

DAYS_PER_YEAR = 365.25
REASON_MAX_CHARS = 200  # `routing_log.reason` VARCHAR(200)

_CALL = 'SELECT "customer_id" FROM "call" WHERE "call_id" = %s'
_ACTIVE_ENTRY = 'SELECT 1 FROM "blacklist_entry" WHERE "customer_ref" = %s AND "released_at" IS NULL AND "expires_at" > %s'
_AGENTS = 'SELECT "agent_id", "display_name", "hired_on" FROM "agent" WHERE "agent_id" = ANY(%s)'
_INSERT_LOG = """
INSERT INTO "routing_log" ("call_id", "is_blacklisted", "assigned_agent_id", "fell_back", "reason", "routed_at")
VALUES (%s, %s, %s, %s, %s, %s)
"""


class PostgresAgentRoutingAdapter(AgentRoutingPort):
    def __init__(self, connect: ConnectionFactory, now=lambda: datetime.now(timezone.utc)) -> None:
        self._connect = connect
        self._now = now

    async def route_call(self, call_id: str, candidate_ids: tuple[str, ...]) -> RoutedCall:
        now = self._now()
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_CALL, (call_id,))
                call = await cur.fetchone()
                if call is None:
                    raise CallNotStartedError(call_id)
                customer_ref = call[0]
                is_blacklisted = False
                if customer_ref is not None:
                    await cur.execute(_ACTIVE_ENTRY, (customer_ref, now))
                    is_blacklisted = await cur.fetchone() is not None

                rows = []
                if candidate_ids:
                    await cur.execute(_AGENTS, (list(candidate_ids),))
                    rows = await cur.fetchall()
                known = {agent_id: (name, hired_on) for agent_id, name, hired_on in rows}
                profiles = [
                    AgentProfile(agent_id=a, name=known[a][0],
                                 tenure_years=0.0 if known[a][1] is None else (now.date() - known[a][1]).days / DAYS_PER_YEAR)
                    for a in candidate_ids if a in known
                ]
                veteran_years = await read_veteran_years(cur)
                decision = route(customer_ref=customer_ref or "", is_blacklisted=is_blacklisted,
                                 candidates=profiles, veteran_years=veteran_years)
                await cur.execute(_INSERT_LOG, (call_id, decision.is_blacklisted, decision.agent_id, decision.fell_back,
                                                decision.reason[:REASON_MAX_CHARS], now))
            await conn.commit()
        return RoutedCall(call_id=call_id, decision=decision, customer_identified=customer_ref is not None,
                          veteran_years=veteran_years, unknown_candidates=tuple(a for a in candidate_ids if a not in known))
