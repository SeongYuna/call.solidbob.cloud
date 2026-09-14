# Requirement: F-2
"""ClosureRecordPort 의 PostgreSQL 구현 — `closure`(헤더) 한 행 + `closure_item`(서류별) 여러 행을 한 트랜잭션에."""

from __future__ import annotations

from datetime import datetime, timezone

from hub.app.dtos.closure_verdict_dto import ClosureVerdict
from hub.app.ports.output.closure_record_port import ClosureRecordPort

from .connection import ConnectionFactory

_INSERT_CLOSURE = """
INSERT INTO "closure" ("call_id", "procedure", "reason", "detected", "verdict", "source_doc_id", "decided_at")
VALUES (%s, %s, %s, %s, %s, %s, %s)
RETURNING "closure_id"
"""
_INSERT_ITEM = 'INSERT INTO "closure_item" ("closure_id", "rank", "document_name", "informed") VALUES (%s, %s, %s, %s)'


class PostgresClosureRepository(ClosureRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def record(self, verdict: ClosureVerdict) -> None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_INSERT_CLOSURE, (
                    verdict.call_id, verdict.procedure, (verdict.reason or None) and verdict.reason[:100],
                    verdict.detected, verdict.verdict, verdict.source.doc_id if verdict.source else None,
                    datetime.now(timezone.utc),
                ))
                closure_id = (await cur.fetchone())[0]
                await cur.executemany(
                    _INSERT_ITEM,
                    [(closure_id, rank, name[:60], informed) for rank, (name, informed) in enumerate(verdict.evidence.items(), 1)],
                )
            await conn.commit()
