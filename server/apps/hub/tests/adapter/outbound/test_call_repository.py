# Requirement: 7.3절 전사 이벤트, QUA-1
"""가짜 커넥션으로 `call` 리포지토리를 검증 — INSERT 인자·멱등·커밋."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from hub.adapter.outbound.postgres.call_repository import PostgresCallRepository
from hub.app.dtos.call_start_dto import CallStarted


class _FakeCursor:
    def __init__(self, log: list, rowcount: int):
        self._log = log
        self.rowcount = rowcount

    async def execute(self, sql, args=None):
        self._log.append((" ".join(sql.split()), args))
        return self


class _FakeConnection:
    def __init__(self, log: list, rowcount: int):
        self._log = log
        self._rowcount = rowcount
        self.committed = False

    @asynccontextmanager
    async def cursor(self):
        yield _FakeCursor(self._log, self._rowcount)

    async def commit(self):
        self.committed = True


def _run(rowcount: int):
    log, holder = [], []

    @asynccontextmanager
    async def _connect():
        conn = _FakeConnection(log, rowcount)
        holder.append(conn)
        yield conn

    call = CallStarted(call_id="test-c001", domain="dasan", stt_engine="mock", channel_count=1,
                       started_at=datetime(2026, 9, 10, tzinfo=timezone.utc), status="in_progress", created=True)
    created = asyncio.run(PostgresCallRepository(_connect).record(call))
    return created, log, holder[0]


def test_새_통화는_INSERT하고_커밋한다():
    created, log, conn = _run(rowcount=1)
    assert created is True and conn.committed is True
    sql, args = log[0]
    assert sql.startswith('INSERT INTO "call"') and 'ON CONFLICT ("call_id") DO NOTHING' in sql
    assert args[0] == "test-c001" and args[1] == "dasan" and args[4] == "mock" and args[5] == "in_progress"


def test_이미_있으면_False를_돌려주고_덮어쓰지_않는다():
    created, log, _ = _run(rowcount=0)
    assert created is False
    assert "DO UPDATE" not in log[0][0]
