# Requirement: C-6, SEC-1
"""CallGuardRecordPort 의 PostgreSQL 구현 — `call_guard_flag` 에 쓴다.

**구간은 발화 단위로 갈아끼운다.** 같은 확정 발화가 다시 오면 `transcript_segment.text` 가 UPSERT 로
바뀌므로, 옛 탐지를 남기면 지금 자막에 없는 표현이 기록에 남는다 — `masking_event` 와 같은 처리다.
지우기와 넣기는 **한 트랜잭션**이다. 중간에 실패하면 옛 기록이 그대로 남는다(없어지지 않는다).

**구간이 없는 탐지는 받지 않는다.** `span_start`·`span_end` 는 NOT NULL 이고, 빈 값을 0 으로 채우면
「발화 첫 글자가 걸렸다」는 거짓 기록이 된다.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from hub.app.dtos.call_guard_dto import CallGuardFlag
from hub.app.ports.output.call_guard_record_port import CallGuardRecordPort

from .connection import ConnectionFactory

_DELETE = 'DELETE FROM "call_guard_flag" WHERE "call_id" = %s AND "segment_id" = %s'

_INSERT = """
INSERT INTO "call_guard_flag"
    ("call_id", "segment_id", "category", "phrase", "span_start", "span_end", "source_doc_id", "detected_at")
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


class PostgresCallGuardFlagRepository(CallGuardRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def replace(self, call_id: str, segment_id: int, flags: Sequence[CallGuardFlag]) -> None:
        missing = [f.category for f in flags if f.span_start is None]
        if missing:
            raise ValueError(f"구간(span)이 없는 콜 가드 탐지는 저장할 수 없습니다: {missing}")

        now = datetime.now(timezone.utc)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_DELETE, (call_id, segment_id))
                if flags:
                    await cur.executemany(
                        _INSERT,
                        [
                            (call_id, segment_id, f.category, f.phrase, f.span_start, f.span_end,
                             f.source_doc_id, now)
                            for f in flags
                        ],
                    )
            await conn.commit()
