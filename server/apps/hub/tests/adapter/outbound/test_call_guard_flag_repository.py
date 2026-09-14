# Requirement: C-6, SEC-1, QUA-1
"""콜 가드 신호 저장. 가짜 커넥션으로 모양을, `@pytest.mark.integration` 으로 실제 스키마를 본다."""

import asyncio
from contextlib import asynccontextmanager

import pytest

from hub.adapter.outbound.postgres.call_guard_flag_repository import PostgresCallGuardFlagRepository
from hub.app.dtos.call_guard_dto import CallGuardFlag

FLAG = CallGuardFlag(category="threat", phrase="가만 안 둬", source_doc_id="DASAN-MANUAL-5.2", span=(5, 11))


class _FakeCursor:
    def __init__(self, log):
        self._log = log

    async def executemany(self, sql, rows):
        self._log.append(("executemany", " ".join(sql.split()), rows))


class _FakeConnection:
    def __init__(self, log):
        self._log = log

    @asynccontextmanager
    async def cursor(self):
        yield _FakeCursor(self._log)

    async def commit(self):
        self._log.append(("commit", "", None))


def _repo(log):
    @asynccontextmanager
    async def connect():
        yield _FakeConnection(log)

    return PostgresCallGuardFlagRepository(connect)


def test_신호마다_한_행을_넣고_커밋한다():
    log = []
    asyncio.run(_repo(log).record("c_001", 7, (FLAG, FLAG)))
    kind, sql, rows = log[0]
    assert kind == "executemany" and 'INSERT INTO "call_guard_flag"' in sql
    assert [r[:7] for r in rows] == [("c_001", 7, "threat", "가만 안 둬", 5, 11, "DASAN-MANUAL-5.2")] * 2
    assert log[-1][0] == "commit"


def test_위치가_없는_신호는_저장하지_않는다():
    """span 을 0 으로 지어내지 않는다 — 스포크 구현이 틀린 것이라 500 으로 드러나야 한다."""
    log = []
    with pytest.raises(RuntimeError):
        asyncio.run(_repo(log).record("c_001", 7, (CallGuardFlag(category="insult", phrase="병신"),)))
    assert log == []


def test_너무_긴_표현은_컬럼_길이로_자른다():
    log = []
    long = CallGuardFlag(category="insult", phrase="가" * 250, span=(0, 250))
    asyncio.run(_repo(log).record("c_001", 7, (long,)))
    assert len(log[0][2][0][3]) == 200


@pytest.mark.integration
def test_실제_DB에_신호가_전사를_참조해_저장된다(integration_settings):
    from hub.adapter.outbound.postgres.connection import build_connection_factory
    from hub.adapter.outbound.postgres.transcript_segment_repository import PostgresTranscriptSegmentRepository
    from hub.app.dtos import TranscriptEvent

    connect = build_connection_factory(integration_settings)
    call_id = "it_c6_001"

    async def scenario():
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM call_guard_flag WHERE call_id=%s", (call_id,))
                await cur.execute("DELETE FROM masking_event WHERE call_id=%s", (call_id,))
                await cur.execute("DELETE FROM transcript_segment WHERE call_id=%s", (call_id,))
                await cur.execute('DELETE FROM "call" WHERE call_id=%s', (call_id,))
                await cur.execute(
                    'INSERT INTO "call" (call_id, domain, started_at, channel_count, stt_engine, status)'
                    " VALUES (%s,'dasan',NOW(),1,'google-stt','closed')",
                    (call_id,),
                )
            await conn.commit()
        await PostgresTranscriptSegmentRepository(connect).record(
            TranscriptEvent(call_id=call_id, segment_id=3, speaker="customer", text="너 가만 안 둬", is_final=True)
        )
        await PostgresCallGuardFlagRepository(connect).record(
            # 실제 탐지기처럼 근거 조항을 붙인다 — `document` 가 비어 있어도 저장이 실패하면 안 된다
            call_id, 3, (CallGuardFlag(category="threat", phrase="가만 안 둬", source_doc_id="DASAN-MANUAL-5.2", span=(2, 8)),)
        )
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT category, phrase, span_start, span_end FROM call_guard_flag WHERE call_id=%s", (call_id,)
                )
                return await cur.fetchall()

    assert asyncio.run(scenario()) == [("threat", "가만 안 둬", 2, 8)]


@pytest.mark.integration
def test_실제_DB에서_저장한_신호를_필터로_다시_읽는다(integration_settings):
    from hub.adapter.outbound.postgres.call_guard_flag_query_repository import PostgresCallGuardFlagQueryRepository
    from hub.adapter.outbound.postgres.connection import build_connection_factory

    connect = build_connection_factory(integration_settings)
    test_실제_DB에_신호가_전사를_참조해_저장된다(integration_settings)  # it_c6_001 에 threat 1건을 만든다

    async def scenario():
        repo = PostgresCallGuardFlagQueryRepository(connect)
        return (await repo.list_flags("it_c6_001", "threat", 10, 0), await repo.count_flags("it_c6_001", "insult"))

    flags, insult_total = asyncio.run(scenario())
    assert [(f.category, f.phrase, f.span) for f in flags] == [("threat", "가만 안 둬", (2, 8))]
    assert insult_total == 0
