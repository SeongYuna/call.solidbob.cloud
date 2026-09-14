# Requirement: D-5, QUA-1
"""D-5 기록 — 화자 단위 갈아끼우기. 실제 DB 검증은 integration."""

import asyncio
from contextlib import asynccontextmanager

import pytest

from hub.adapter.outbound.postgres.voice_outlier_repository import PostgresVoiceOutlierRepository
from hub.app.dtos import VoiceOutlier


class _Cursor:
    def __init__(self, log):
        self._log = log

    async def execute(self, sql, args=None):
        self._log.append(("execute", " ".join(sql.split()), args))

    async def executemany(self, sql, args):
        self._log.append(("executemany", " ".join(sql.split()), list(args)))


class _Conn:
    def __init__(self, log):
        self._log = log

    @asynccontextmanager
    async def cursor(self):
        yield _Cursor(self._log)

    async def commit(self):
        self._log.append(("commit", "", None))


def _repo(log):
    @asynccontextmanager
    async def connect():
        yield _Conn(log)

    return PostgresVoiceOutlierRepository(connect)


def test_그_화자의_옛_판정만_지우고_새로_넣는다():
    log = []
    asyncio.run(_repo(log).replace("c_001", "customer", [VoiceOutlier(12, "customer", 4.2, 16)]))
    assert log[0][1].startswith('DELETE FROM "voice_outlier"') and log[0][2] == ("c_001", "customer")
    [row] = log[1][2]
    assert row[:5] == ("c_001", 12, "customer", 4.2, 16)
    assert log[-1][0] == "commit"


def test_다른_화자의_발화가_섞이면_DB_에_닿기_전에_거부한다():
    log = []
    with pytest.raises(ValueError):
        asyncio.run(_repo(log).replace("c_001", "customer", [VoiceOutlier(3, "agent", 4.0, 9)]))
    assert log == []


def test_기준선_없는_이상_구간은_만들_수_없다():
    with pytest.raises(ValueError):
        VoiceOutlier(1, "customer", 5.0, 0)


@pytest.mark.integration
def test_실제_DB에_화자별로_갈아끼워진다(integration_settings):
    from hub.adapter.outbound.postgres.connection import build_connection_factory
    from hub.adapter.outbound.postgres.transcript_segment_repository import PostgresTranscriptSegmentRepository
    from hub.app.dtos import TranscriptEvent

    connect = build_connection_factory(integration_settings)
    call_id = "it_d5_001"

    async def scenario():
        async with connect() as conn:
            async with conn.cursor() as cur:
                for table in ("voice_outlier", "call_guard_flag", "masking_event", "transcript_segment"):
                    await cur.execute(f'DELETE FROM "{table}" WHERE call_id=%s', (call_id,))
                await cur.execute('DELETE FROM "call" WHERE call_id=%s', (call_id,))
                await cur.execute(
                    'INSERT INTO "call" (call_id, domain, started_at, channel_count, stt_engine, status)'
                    " VALUES (%s,'dasan',NOW(),1,'google-stt','closed')", (call_id,))
            await conn.commit()
        segments = PostgresTranscriptSegmentRepository(connect)
        for sid, speaker in ((1, "customer"), (2, "agent"), (3, "customer")):
            await segments.record(TranscriptEvent(call_id=call_id, segment_id=sid, speaker=speaker,
                                                  text="…", is_final=True))
        repo = PostgresVoiceOutlierRepository(connect)
        await repo.replace(call_id, "customer", [VoiceOutlier(1, "customer", 4.1, 12)])
        await repo.replace(call_id, "agent", [VoiceOutlier(2, "agent", -3.9, 12)])
        await repo.replace(call_id, "customer", [VoiceOutlier(3, "customer", 5.0, 13)])  # 재판정
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT speaker, segment_id, baseline_n FROM voice_outlier"
                                  " WHERE call_id=%s ORDER BY segment_id", (call_id,))
                return await cur.fetchall()

    assert [tuple(r) for r in asyncio.run(scenario())] == [("agent", 2, 12), ("customer", 3, 13)]
