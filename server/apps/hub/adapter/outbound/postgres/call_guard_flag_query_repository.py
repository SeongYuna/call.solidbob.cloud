# Requirement: C-6
"""CallGuardFlagQueryPort 의 PostgreSQL 구현 — 최근 탐지순. 같은 시각이면 `id` 로 순서를 고정한다."""

from __future__ import annotations

from hub.app.dtos.call_guard_flag_list_dto import CallGuardFlagRecord
from hub.app.ports.output.call_guard_flag_query_port import CallGuardFlagQueryPort

from .connection import ConnectionFactory

_SELECT = """
SELECT "id", "call_id", "segment_id", "category", "phrase", "span_start", "span_end", "source_doc_id", "detected_at"
FROM "call_guard_flag"
"""


def _where(call_id: str | None, category: str | None) -> tuple[str, tuple]:
    clauses, args = [], []
    if call_id is not None:
        clauses.append('"call_id" = %s')
        args.append(call_id)
    if category is not None:
        clauses.append('"category" = %s')
        args.append(category)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), tuple(args)


class PostgresCallGuardFlagQueryRepository(CallGuardFlagQueryPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def list_flags(self, call_id, category, limit, offset) -> list[CallGuardFlagRecord]:
        where, args = _where(call_id, category)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    _SELECT + where + ' ORDER BY "detected_at" DESC, "id" DESC LIMIT %s OFFSET %s', (*args, limit, offset)
                )
                rows = await cur.fetchall()
        return [
            CallGuardFlagRecord(id=int(r[0]), call_id=r[1], segment_id=int(r[2]), category=r[3], phrase=r[4],
                                span=(int(r[5]), int(r[6])), source_doc_id=r[7], detected_at=r[8])
            for r in rows
        ]

    async def count_flags(self, call_id, category) -> int:
        where, args = _where(call_id, category)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT COUNT(*) FROM "call_guard_flag"' + where, args)
                row = await cur.fetchone()
        return int(row[0]) if row else 0
