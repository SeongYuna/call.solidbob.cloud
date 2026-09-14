# Requirement: A-1, SEC-1
"""TranscriptQueryPort 의 PostgreSQL 구현.

`segment_id` 오름차순으로 준다 — 발화 순서다. 정렬을 허브로 올리면 인덱스를 못 쓰고
페이지 경계에서 순서가 어긋난다.

**마스킹 완료본만 나간다** (SEC-1). `transcript_segment.text` 에 원문이 없으므로 구조적으로 보장된다.
"""

from __future__ import annotations

from hub.app.dtos.transcript_dto import MaskedSpan, TranscriptEvent
from hub.app.ports.output.transcript_query_port import TranscriptQueryPort

from .connection import ConnectionFactory

_LIST = """
SELECT s."segment_id", s."speaker", s."text", s."is_final", s."utterance_end_ms"
FROM "transcript_segment" s
WHERE s."call_id" = %s
ORDER BY s."segment_id"
LIMIT %s OFFSET %s
"""

_COUNT = 'SELECT COUNT(*) FROM "transcript_segment" WHERE "call_id" = %s'

# `segment_id` 는 통화 안에서의 순번이다(`decisions/205`) — `call_id` 로 거르지 않으면
# 다른 통화의 같은 순번 발화에 붙은 마스킹 구간이 섞여 나온다.
_SPANS = """
SELECT "segment_id", "pattern", "span_start", "span_end"
FROM "masking_event"
WHERE "call_id" = %s AND "segment_id" IN ({placeholders})
ORDER BY "segment_id", "span_start"
"""


class PostgresTranscriptQueryRepository(TranscriptQueryPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def list_segments(self, call_id: str, limit: int, offset: int) -> list[TranscriptEvent]:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LIST, (call_id, limit, offset))
                rows = await cur.fetchall()
                if not rows:
                    return []

                # 마스킹 구간은 별도 테이블이다 — 세그먼트마다 쿼리하면 N+1 이 된다
                ids = [r[0] for r in rows]
                await cur.execute(
                    _SPANS.format(placeholders=", ".join(["%s"] * len(ids))),
                    (call_id, *ids),
                )
                span_rows = await cur.fetchall()

        spans: dict[int, list[MaskedSpan]] = {}
        for segment_id, pattern, start, end in span_rows:
            spans.setdefault(segment_id, []).append(MaskedSpan(type=pattern, span=(start, end)))

        return [
            TranscriptEvent(
                call_id=call_id,
                segment_id=r[0],
                speaker=r[1],
                text=r[2],  # 마스킹 완료본 (SEC-1)
                is_final=bool(r[3]),
                utterance_end_ms=r[4],
                masked=tuple(spans.get(r[0], ())),
            )
            for r in rows
        ]

    async def count_segments(self, call_id: str) -> int:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_COUNT, (call_id,))
                row = await cur.fetchone()
        return int(row[0]) if row else 0
