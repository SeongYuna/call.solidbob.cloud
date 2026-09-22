# Requirement: J-2, J-6, SEC-1
"""BlacklistEvidencePort 의 PostgreSQL 구현.

- **자막은 `transcript_segment.text`(마스킹본)에서만 자른다.** 콜 가드가 잡힌 고객 발화를 우선 싣고,
  없으면 마지막 고객 발화 몇 개를 싣는다. 길이를 제한한다 — 요청 1건에 통화 전체를 옮겨 적지 않는다
- 통화 길이는 `ended_at - started_at`, 아직 안 끝났으면 마지막 발화 종료 시각이다
- `distress` 건수는 **돌려주되 저장하지 않는다**(`decisions/205` ④) — 저장 여부는 요청 리포지토리가 정한다
- **온도 이상(`voice_outlier`)은 판정이 붙어 있을 때만 센다**(`decisions/316`). 서버 요청 경로에는 D-5 판정이 없어
  (`voice_outlier` 에 쓰는 곳이 평가 하네스뿐 — 09-22 확인) 세면 늘 0 이고, 관리자는 그 0 을 「이상 없음」으로 읽는다.
  붙지 않았으면 None(「미측정」)을 돌려준다
"""

from __future__ import annotations

from hub.app.dtos.blacklist_dto import RequestEvidence
from hub.app.dtos.blacklist_request_create_dto import CallEvidence
from hub.app.ports.output.blacklist_evidence_port import BlacklistEvidencePort

from .connection import ConnectionFactory

_CALL = """
SELECT c."customer_id",
       COALESCE(EXTRACT(EPOCH FROM (c."ended_at" - c."started_at")),
                (SELECT MAX(s."utterance_end_ms") FROM "transcript_segment" s WHERE s."call_id" = c."call_id") / 1000.0,
                0)
FROM "call" c WHERE c."call_id" = %s
"""
_GUARD_COUNTS = 'SELECT "category", COUNT(*) FROM "call_guard_flag" WHERE "call_id" = %s GROUP BY "category"'
_OUTLIERS = 'SELECT COUNT(*) FROM "voice_outlier" WHERE "call_id" = %s'
_FLAGGED_TEXT = """
SELECT s."text" FROM "transcript_segment" s
WHERE s."call_id" = %s AND s."speaker" = 'customer'
  AND s."segment_id" IN (SELECT f."segment_id" FROM "call_guard_flag" f WHERE f."call_id" = %s)
ORDER BY s."segment_id"
"""
_LAST_CUSTOMER_TEXT = """
SELECT s."text" FROM "transcript_segment" s
WHERE s."call_id" = %s AND s."speaker" = 'customer'
ORDER BY s."segment_id" DESC LIMIT %s
"""

EXCERPT_MAX_CHARS = 1000
_FALLBACK_SEGMENTS = 3


class PostgresBlacklistEvidenceRepository(BlacklistEvidencePort):
    def __init__(self, connect: ConnectionFactory, *, voice_outliers_wired: bool = False) -> None:
        self._connect = connect
        self._voice_outliers_wired = voice_outliers_wired

    async def collect(self, call_id: str) -> CallEvidence | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_CALL, (call_id,))
                call = await cur.fetchone()
                if call is None:
                    return None
                await cur.execute(_GUARD_COUNTS, (call_id,))
                counts = {category: int(n) for category, n in await cur.fetchall()}
                outliers = None
                if self._voice_outliers_wired:
                    await cur.execute(_OUTLIERS, (call_id,))
                    outliers = int((await cur.fetchone())[0])
                await cur.execute(_FLAGGED_TEXT, (call_id, call_id))
                texts = [r[0] for r in await cur.fetchall()]
                if not texts:
                    await cur.execute(_LAST_CUSTOMER_TEXT, (call_id, _FALLBACK_SEGMENTS))
                    texts = [r[0] for r in reversed(await cur.fetchall())]

        return CallEvidence(
            customer_ref=call[0],
            evidence=RequestEvidence(
                call_duration_s=int(float(call[1] or 0)),
                insult_count=counts.get("insult", 0),
                threat_count=counts.get("threat", 0),
                sexual_count=counts.get("sexual", 0),
                distress_count=counts.get("distress", 0),
                temperature_outliers=outliers,
            ),
            context_excerpt="\n".join(texts)[:EXCERPT_MAX_CHARS],
        )
