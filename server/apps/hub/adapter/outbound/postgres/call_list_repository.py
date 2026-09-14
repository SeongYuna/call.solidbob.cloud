# Requirement: D-1, D-2
"""CallListPort 의 PostgreSQL 구현 — `call` 을 최근 시작순으로 준다. 같은 시각이면 `call_id` 로 순서를 고정한다
(안 그러면 페이지를 넘길 때 같은 행이 두 번 나오거나 빠진다)."""

from __future__ import annotations

from hub.app.dtos.call_list_dto import CallListItem
from hub.app.ports.output.call_list_port import CallListPort

from .connection import ConnectionFactory

_COLUMNS = """
SELECT "call_id", "domain", "started_at", "ended_at", "status", "stt_engine", "channel_count",
       "customer_id", "inquiry_type", "summary_confirmed_at" IS NOT NULL
FROM "call"
"""
_ORDER = ' ORDER BY "started_at" DESC, "call_id" DESC LIMIT %s OFFSET %s'
_BY_CUSTOMER = ' WHERE "customer_id" = %s'


class PostgresCallListRepository(CallListPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def list_calls(self, limit: int, offset: int, customer_id: str | None) -> list[CallListItem]:
        if customer_id is None:
            sql, args = _COLUMNS + _ORDER, (limit, offset)
        else:
            sql, args = _COLUMNS + _BY_CUSTOMER + _ORDER, (customer_id, limit, offset)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                rows = await cur.fetchall()
        return [
            CallListItem(
                call_id=r[0], domain=r[1], started_at=r[2], ended_at=r[3], status=r[4], stt_engine=r[5],
                channel_count=int(r[6]), customer_id=r[7], inquiry_type=r[8], summary_confirmed=bool(r[9]),
            )
            for r in rows
        ]

    async def count_calls(self, customer_id: str | None) -> int:
        if customer_id is None:
            sql, args = 'SELECT COUNT(*) FROM "call"', ()
        else:
            sql, args = 'SELECT COUNT(*) FROM "call"' + _BY_CUSTOMER, (customer_id,)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                row = await cur.fetchone()
        return int(row[0]) if row else 0
