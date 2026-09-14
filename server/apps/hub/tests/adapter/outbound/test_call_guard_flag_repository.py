# Requirement: C-6, SEC-1, QUA-1
"""가짜 커넥션으로 C-6 기록 규칙을 고정한다 — 발화 단위 갈아끼우기 · 구간 없는 탐지 거부.
실제 DB 검증(외래키·CHECK)은 아래 integration 테스트다."""

import asyncio
from contextlib import asynccontextmanager

import pytest

from hub.adapter.outbound.postgres.call_guard_flag_repository import PostgresCallGuardFlagRepository
from hub.app.dtos import CallGuardFlag

MASKED = "제 번호는 *********** 인데 이 개새끼야"


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

    return PostgresCallGuardFlagRepository(connect)


def _flag():
    start = MASKED.index("개새끼")
    return CallGuardFlag(category="insult", phrase="개새끼", source_doc_id="DASAN-MANUAL-5.1",
                         span_start=start, span_end=start + 3)


def test_같은_발화의_옛_탐지를_지우고_새로_넣은_뒤_커밋한다():
    log = []
    asyncio.run(_repo(log).replace("c_001", 7, [_flag()]))
    assert [kind for kind, _, _ in log] == ["execute", "executemany", "commit"]
    assert log[0][1].startswith('DELETE FROM "call_guard_flag"') and log[0][2] == ("c_001", 7)
    [row] = log[1][2]
    assert row[:7] == ("c_001", 7, "insult", "개새끼", MASKED.index("개새끼"), MASKED.index("개새끼") + 3,
                       "DASAN-MANUAL-5.1")


def test_걸린_것이_없어도_옛_탐지는_지운다():
    """확정본이 다시 와서 욕설이 사라졌으면 기록에서도 사라져야 한다."""
    log = []
    asyncio.run(_repo(log).replace("c_001", 7, []))
    assert [kind for kind, _, _ in log] == ["execute", "commit"]


def test_구간이_없는_탐지는_DB_에_닿기_전에_거부한다():
    log = []
    with pytest.raises(ValueError):
        asyncio.run(_repo(log).replace("c_001", 7, [CallGuardFlag(category="threat", phrase="가만 안 둬")]))
    assert log == []


def test_구간은_함께_주거나_함께_비워야_한다():
    with pytest.raises(ValueError):
        CallGuardFlag(category="insult", phrase="x", span_start=1)
    with pytest.raises(ValueError):
        CallGuardFlag(category="insult", phrase="x", span_start=3, span_end=3)


# ── 실제 PostgreSQL (기본 실행에서 제외) ─────────────────────────────────────────────


@pytest.mark.integration
def test_실제_DB에_마스킹된_자막의_구간으로_남고_다시_보내면_갈아끼운다(integration_settings):
    from hub.adapter.outbound.postgres.connection import build_connection_factory
    from hub.adapter.outbound.postgres.transcript_segment_repository import PostgresTranscriptSegmentRepository
    from hub.app.dtos import MaskedSpan, TranscriptEvent

    connect = build_connection_factory(integration_settings)
    call_id = "it_c6_001"

    async def scenario():
        await _reset(connect, call_id)
        await PostgresTranscriptSegmentRepository(connect).record(TranscriptEvent(
            call_id=call_id, segment_id=1, speaker="customer", text=MASKED, is_final=True,
            masked=(MaskedSpan(type="P4", span=(6, 17)),)))
        repo = PostgresCallGuardFlagRepository(connect)
        await repo.replace(call_id, 1, [_flag()])
        await repo.replace(call_id, 1, [_flag()])  # 재전송 — 행이 늘지 않는다
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT f.category, f.phrase, substr(t.text, f.span_start + 1, f.span_end - f.span_start)"
                    " FROM call_guard_flag f JOIN transcript_segment t"
                    " ON t.call_id = f.call_id AND t.segment_id = f.segment_id WHERE f.call_id = %s",
                    (call_id,))
                return await cur.fetchall()

    rows = asyncio.run(scenario())
    assert [tuple(r) for r in rows] == [("insult", "개새끼", "개새끼")]  # 구간이 저장된 자막을 가리킨다


async def _reset(connect, call_id):
    async with connect() as conn:
        async with conn.cursor() as cur:
            # FK 대상 조항 — 적재 스크립트(scripts/seed_documents.py)가 채우는 행을 테스트가 직접 넣는다
            await cur.execute(
                'INSERT INTO "document" (document_id, doc_type, chapter, clause, title, source_path, updated_at)'
                " VALUES ('DASAN-MANUAL-5.1','MANUAL','5','5.1','폭언 발생 시 단계적 대응',"
                " 'knowledge-base/dasan/manual/MANUAL.md', NOW()) ON CONFLICT (document_id) DO NOTHING")
            for table in ("call_guard_flag", "voice_outlier", "masking_event", "transcript_segment"):
                await cur.execute(f'DELETE FROM "{table}" WHERE call_id=%s', (call_id,))
            await cur.execute('DELETE FROM "call" WHERE call_id=%s', (call_id,))
            await cur.execute(
                'INSERT INTO "call" (call_id, domain, started_at, channel_count, stt_engine, status)'
                " VALUES (%s,'dasan',NOW(),1,'google-stt','closed')", (call_id,))
        await conn.commit()
