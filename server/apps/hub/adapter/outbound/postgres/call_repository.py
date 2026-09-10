# Requirement: 7.3절 전사 이벤트
"""CallStartRecordPort 의 PostgreSQL 구현 — `call` 행을 만든다.

`ON CONFLICT DO NOTHING` 으로 멱등이다. 같은 통화를 두 번 알려도 시작 시각·엔진이 덮이지 않는다.
`customer_id`·`agent_id` 는 넣지 않는다 — 둘 다 외래키라 없는 값을 넣으면 실패하고, 이 경로에서는
아직 그 정보가 없다(F-3 반복 문의 연결이 붙을 때 채운다).
"""

from __future__ import annotations

from hub.app.dtos.call_start_dto import CallStarted
from hub.app.ports.output.call_start_record_port import CallStartRecordPort

from .connection import ConnectionFactory

# `call` 은 예약어라 큰따옴표로 감싼다.
_INSERT_CALL = """
INSERT INTO "call"
    ("call_id", "domain", "started_at", "channel_count", "stt_engine", "status")
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT ("call_id") DO NOTHING
"""


class PostgresCallRepository(CallStartRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def record(self, call: CallStarted) -> bool:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                result = await cur.execute(
                    _INSERT_CALL,
                    (call.call_id, call.domain, call.started_at, call.channel_count, call.stt_engine, call.status),
                )
                # psycopg 는 execute 가 커서를 돌려주고, DO NOTHING 으로 건너뛴 행은 rowcount 에 안 잡힌다.
                rowcount = getattr(result, "rowcount", None)
                if rowcount is None:
                    rowcount = getattr(cur, "rowcount", 1)
            await conn.commit()
        return rowcount > 0
