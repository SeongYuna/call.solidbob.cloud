# Requirement: D-1, D-2, QUA-1
"""통화 목록 조회 — 가짜 커넥션으로 SQL 모양을, `@pytest.mark.integration` 으로 실제 정렬·필터를 본다."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from hub.adapter.outbound.postgres.call_list_repository import PostgresCallListRepository

ROW = ("test-1", "dasan", datetime(2026, 9, 14, tzinfo=timezone.utc), None, "in_progress", "google-stt", 2,
       None, None, False)


def _repo(log, rows):
    class _Cursor:
        async def execute(self, sql, args=()):
            log.append((" ".join(sql.split()), args))

        async def fetchall(self):
            return rows

        async def fetchone(self):
            return (len(rows),)

    class _Conn:
        @asynccontextmanager
        async def cursor(self):
            yield _Cursor()

    @asynccontextmanager
    async def connect():
        yield _Conn()

    return PostgresCallListRepository(connect)


def test_최근_시작순_페이지로_읽는다():
    log = []
    items = asyncio.run(_repo(log, [ROW]).list_calls(10, 0, None))
    sql, args = log[0]
    assert 'ORDER BY "started_at" DESC, "call_id" DESC LIMIT %s OFFSET %s' in sql and "WHERE" not in sql
    assert args == (10, 0)
    assert items[0].call_id == "test-1" and items[0].channel_count == 2 and items[0].summary_confirmed is False


def test_고객_필터는_목록과_총수_둘_다에_건다():
    log = []
    repo = _repo(log, [ROW])
    asyncio.run(repo.list_calls(10, 0, "cust-9"))
    asyncio.run(repo.count_calls("cust-9"))
    assert all('WHERE "customer_id" = %s' in sql for sql, _ in log)
    assert log[0][1] == ("cust-9", 10, 0) and log[1][1] == ("cust-9",)


@pytest.mark.integration
def test_실제_DB에서_최근순으로_나온다(integration_settings):
    from hub.adapter.outbound.postgres.connection import build_connection_factory

    connect = build_connection_factory(integration_settings)
    ids = ("it_list_old", "it_list_new")

    async def scenario():
        async with connect() as conn:
            async with conn.cursor() as cur:
                for call_id, started in zip(ids, ("2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z")):
                    await cur.execute('DELETE FROM "call" WHERE call_id=%s', (call_id,))
                    await cur.execute(
                        'INSERT INTO "call" (call_id, domain, started_at, channel_count, stt_engine, status)'
                        " VALUES (%s,'dasan',%s,1,'google-stt','closed')",
                        (call_id, started),
                    )
            await conn.commit()
        repo = PostgresCallListRepository(connect)
        listed = [c.call_id for c in await repo.list_calls(200, 0, None) if c.call_id in ids]
        return listed, await repo.count_calls(None)

    listed, total = asyncio.run(scenario())
    assert listed == ["it_list_new", "it_list_old"]
    assert total >= 2


@pytest.mark.integration
def test_실제_DB에서_발신_번호로_이은_고객의_통화만_거른다(integration_settings):
    """A-5 재상담 이력의 실제 경로 — 통화 시작(HMAC) → customer 행 → 목록 필터 (decisions/304)."""
    from hub.adapter.outbound.hmac_customer_ref_adapter import HmacCustomerRefAdapter
    from hub.adapter.outbound.postgres.call_repository import PostgresCallRepository
    from hub.adapter.outbound.postgres.connection import build_connection_factory
    from hub.app.use_cases.call_start_interactor import CallStartInteractor
    from hub.app.dtos.call_start_dto import CallStartCommand

    connect = build_connection_factory(integration_settings)
    ref = HmacCustomerRefAdapter("it-key")
    customer = ref.ref("010-5555-0001")
    ids = ("it_cust_a1", "it_cust_a2", "it_cust_b1")

    async def scenario():
        async with connect() as conn:
            async with conn.cursor() as cur:
                for call_id in ids:
                    await cur.execute('DELETE FROM "call" WHERE call_id=%s', (call_id,))
            await conn.commit()
        start = CallStartInteractor(PostgresCallRepository(connect), customer_ref=ref)
        for call_id, phone in zip(ids, ("01055550001", "+82 10 5555 0001", "010-5555-0002")):
            await start.start(CallStartCommand(call_id=call_id, domain="dasan", stt_engine="google-stt",
                                               channel_count=1, caller_phone=phone))
        repo = PostgresCallListRepository(connect)
        return [c.call_id for c in await repo.list_calls(50, 0, customer)], await repo.count_calls(customer)

    listed, total = asyncio.run(scenario())
    assert sorted(listed) == ["it_cust_a1", "it_cust_a2"] and total == 2
