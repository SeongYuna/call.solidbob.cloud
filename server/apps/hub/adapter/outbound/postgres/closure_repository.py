# Requirement: F-2
"""ClosureRecordPort 의 PostgreSQL 구현 — `closure`(헤더) 한 행 + `closure_item`(서류별) 여러 행을 한 트랜잭션에."""

from __future__ import annotations

from datetime import datetime, timezone

from hub.app.dtos.closure_verdict_dto import ClosureVerdict
from hub.app.ports.output.closure_record_port import ClosureRecordPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

from .connection import ConnectionFactory

_INSERT_CLOSURE = """
INSERT INTO "closure" ("call_id", "procedure", "reason", "detected", "verdict", "source_doc_id", "decided_at")
VALUES (%s, %s, %s, %s, %s, %s, %s)
RETURNING "closure_id"
"""
_FOREIGN_KEY_VIOLATION = "23503"
_INSERT_ITEM = 'INSERT INTO "closure_item" ("closure_id", "rank", "document_name", "informed") VALUES (%s, %s, %s, %s)'


class PostgresClosureRepository(ClosureRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def record(self, verdict: ClosureVerdict) -> None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(_INSERT_CLOSURE, (
                        verdict.call_id, verdict.procedure, (verdict.reason or None) and verdict.reason[:100],
                        verdict.detected, verdict.verdict, verdict.source.doc_id if verdict.source else None,
                        datetime.now(timezone.utc),
                    ))
                except Exception as exc:
                    # 이 INSERT 가 참조하는 외래키는 call 하나뿐이다 — 통화 시작이 안 왔다(호출자 실수, 404 — `decisions/318`).
                    # 전에는 원시 FK 오류가 그대로 올라가 500 이었다
                    if getattr(exc, "sqlstate", None) == _FOREIGN_KEY_VIOLATION:
                        raise CallNotStartedError(verdict.call_id) from exc
                    raise
                closure_id = (await cur.fetchone())[0]
                await cur.executemany(
                    _INSERT_ITEM,
                    [(closure_id, rank, name[:60], informed) for rank, (name, informed) in enumerate(verdict.evidence.items(), 1)],
                )
            await conn.commit()
