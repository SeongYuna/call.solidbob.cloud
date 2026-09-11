# Requirement: 7.3절 전사 이벤트, C-5, SEC-1, QUA-1
"""가짜 커넥션으로 리포지토리를 검증한다 — 실제 PostgreSQL 없이 SEC-1 과 interim 규칙을 고정한다.

진짜 DB 를 쓰는 검증은 @pytest.mark.integration 으로 따로 둔다(기본 실행에서 빠진다).
"""

import asyncio
from contextlib import asynccontextmanager

from hub.adapter.outbound.postgres.transcript_segment_repository import PostgresTranscriptSegmentRepository
from hub.app.dtos import MaskedSpan, TranscriptEvent

RAW = "제 번호는 01012345678 입니다"
MASKED = "제 번호는 *********** 입니다"


class _FakeCursor:
    def __init__(self, log: list):
        self._log = log

    async def execute(self, sql, args=None):
        self._log.append(("execute", " ".join(sql.split()), args))

    async def executemany(self, sql, args):
        self._log.append(("executemany", " ".join(sql.split()), args))


class _FakeConnection:
    def __init__(self, log: list):
        self._log = log
        self.committed = False

    @asynccontextmanager
    async def cursor(self):
        yield _FakeCursor(self._log)

    async def commit(self):
        self.committed = True
        self._log.append(("commit", "", None))


def _factory(log: list, holder: list):
    @asynccontextmanager
    async def _connect():
        conn = _FakeConnection(log)
        holder.append(conn)
        yield conn

    return _connect


def _record(event: TranscriptEvent):
    log, holder = [], []
    repo = PostgresTranscriptSegmentRepository(_factory(log, holder))
    asyncio.run(repo.record(event))
    return log, holder


def _final(**kw) -> TranscriptEvent:
    base = dict(call_id="c_001", segment_id=31, speaker="customer", text=MASKED,
                is_final=True, utterance_end_ms=2600,
                masked=(MaskedSpan(type="P4", span=(6, 17)),))
    return TranscriptEvent(**{**base, **kw})


def test_interim은_저장하지_않는다():
    """7.3절: DB 에는 is_final=true 만 저장한다. 20초에 199건(V4 실측)이 그대로 쌓이면 안 된다."""
    log, holder = _record(_final(is_final=False))
    assert log == []
    assert holder == []  # 커넥션조차 열지 않는다


def test_확정본은_저장하고_커밋한다():
    log, holder = _record(_final())
    kinds = [k for k, _, _ in log]
    assert kinds == ["execute", "execute", "executemany", "commit"]
    assert holder[0].committed is True


def test_마스킹된_텍스트만_넘긴다():
    """SEC-1 — 원문이 쿼리 인자 어디에도 없어야 한다."""
    log, _ = _record(_final())
    flat = repr(log)
    assert MASKED in flat
    assert RAW not in flat
    assert "01012345678" not in flat


def test_마스킹_구간을_다시_넣기_전에_지운다():
    """같은 segment 를 다시 받으면 이전 구간이 남아 새 마스킹과 섞인다."""
    log, _ = _record(_final())
    delete = [row for row in log if 'DELETE FROM "masking_event"' in row[1]]
    assert len(delete) == 1
    assert delete[0][2] == ("c_001", 31)


def test_UPSERT_충돌_키는_call_id와_segment_id_복합키다():
    """decisions/205: segment_id 는 통화 안의 순번이다. segment_id 하나로 충돌을 잡으면
    c_002 의 1번 발화가 c_001 의 1번 발화를 덮어쓴다(스키마 QA 에서 실제로 재현됐다)."""
    log, _ = _record(_final())
    upsert = log[0][1]
    assert 'ON CONFLICT ("call_id", "segment_id")' in upsert
    assert 'ON CONFLICT ("segment_id")' not in upsert


def test_마스킹_구간_삭제는_다른_통화의_같은_순번을_건드리지_않는다():
    """call_id 없이 segment_id 로만 지우면 다른 통화의 같은 순번 구간까지 지워진다."""
    log, _ = _record(_final())
    delete = [row for row in log if 'DELETE FROM "masking_event"' in row[1]][0]
    assert '"call_id" = %s AND "segment_id" = %s' in delete[1]


def test_마스킹_구간은_복합_FK_짝인_call_id와_함께_넣는다():
    """masking_event 는 (call_id, segment_id) 로 transcript_segment 를 참조한다 — call_id 가 없으면 NOT NULL 위반."""
    log, _ = _record(_final())
    sql, rows = [(s, a) for k, s, a in log if k == "executemany"][0]
    assert '("call_id", "segment_id", "pattern"' in sql
    assert rows[0][:2] == ("c_001", 31)


class _DbError(Exception):
    """psycopg 오류 흉내 — 리포지토리는 `sqlstate` 만 본다."""

    def __init__(self, sqlstate: str):
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def _record_failing(sqlstate: str):
    class _FailingCursor(_FakeCursor):
        async def execute(self, sql, args=None):
            raise _DbError(sqlstate)

    class _FailingConnection(_FakeConnection):
        @asynccontextmanager
        async def cursor(self):
            yield _FailingCursor(self._log)

    @asynccontextmanager
    async def _connect():
        yield _FailingConnection([])

    return asyncio.run(PostgresTranscriptSegmentRepository(_connect).record(_final()))


def test_통화가_없으면_외래키_위반을_CallNotStartedError로_올린다():
    """decisions/301: 통화 시작이 전사보다 먼저 와야 한다. 그걸 어긴 호출은 500(코드 결함)이 아니다."""
    import pytest

    from hub.app.ports.output import CallNotStartedError

    with pytest.raises(CallNotStartedError) as info:
        _record_failing("23503")
    assert info.value.call_id == "c_001"


def test_외래키_위반이_아닌_DB_오류는_그대로_올린다():
    """연결 끊김·스키마 불일치 같은 진짜 결함까지 409 로 가리면 안 된다."""
    import pytest

    with pytest.raises(_DbError):
        _record_failing("42P10")  # 이번에 실제로 났던 InvalidColumnReference


def test_마스킹_구간이_없으면_insert하지_않는다():
    log, _ = _record(_final(masked=()))
    assert not any(k == "executemany" for k, _, _ in log)


def test_구간은_문자_오프셋_그대로_저장한다():
    """7.3절: span 은 문자(코드포인트) 오프셋이다. byte 로 바꾸면 한글에서 프론트와 어긋난다."""
    log, _ = _record(_final())
    spans = [row for row in log if row[0] == "executemany"][0][2]
    assert spans[0][2:5] == ("P4", 6, 17)


# ── 실제 PostgreSQL 이 필요한 검증 (기본 실행에서 제외 — pytest.ini addopts) ────────────────
#
#    cd infra && docker compose up -d
#    cd ../server && ../.venv/bin/python -m pytest -m integration
#
# DB 는 `integration_settings` 픽스처(server/conftest.py)가 준다 — CI 는 매번 새 DB 에 현재 schema.sql.

import pytest  # noqa: E402

RAW_PHONE = "01012345678"


@pytest.mark.integration
def test_실제_DB에_마스킹본만_저장되고_원문이_없다(integration_settings):
    """SEC-1 최종 확인 — 스키마 리뷰가 아니라 실제 저장 결과로 본다."""
    import asyncio

    from hub.adapter.outbound.postgres.connection import build_connection_factory

    connect = build_connection_factory(integration_settings)
    call_id = "it_sec1_001"
    segment_id = 990001

    async def scenario():
        await _reset_calls(connect, call_id)

        repo = PostgresTranscriptSegmentRepository(connect)
        await repo.record(TranscriptEvent(call_id=call_id, segment_id=segment_id, speaker="customer",
                                          text=MASKED, is_final=True, utterance_end_ms=2600,
                                          masked=(MaskedSpan(type="P4", span=(6, 17)),)))
        # interim 은 저장되지 않아야 한다
        await repo.record(TranscriptEvent(call_id=call_id, segment_id=segment_id + 1, speaker="customer",
                                          text="중간 결과", is_final=False))

        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT text FROM transcript_segment WHERE call_id=%s AND segment_id=%s",
                                  (call_id, segment_id))
                stored = await cur.fetchone()
                await cur.execute("SELECT COUNT(*) FROM transcript_segment WHERE call_id=%s AND segment_id=%s",
                                  (call_id, segment_id + 1))
                interim_rows = (await cur.fetchone())[0]
                await cur.execute("SELECT pattern, span_start, span_end FROM masking_event"
                                  " WHERE call_id=%s AND segment_id=%s", (call_id, segment_id))
                spans = await cur.fetchall()
        return stored[0], interim_rows, spans

    stored_text, interim_rows, spans = asyncio.run(scenario())

    assert stored_text == MASKED
    assert RAW_PHONE not in stored_text  # SEC-1 — 원문이 남지 않는다
    assert interim_rows == 0  # 7.3절 — interim 은 저장하지 않는다
    assert list(spans) == [("P4", 6, 17)]


@pytest.mark.integration
def test_실제_DB에서_두_통화의_같은_순번_발화가_각각_남는다(integration_settings):
    """decisions/205 · w4-schema-qa-followup ① — 고치기 전에는 c_002 의 1번 발화가 c_001 의 1번을 덮었다.
    같은 발화를 다시 보내는 UPSERT(확정본 교체)는 그 통화 안에서만 일어나야 한다."""
    import asyncio

    from hub.adapter.outbound.postgres.connection import build_connection_factory
    from hub.adapter.outbound.postgres.transcript_query_repository import PostgresTranscriptQueryRepository

    connect = build_connection_factory(integration_settings)
    first, second = "it_pk_001", "it_pk_002"

    async def scenario():
        await _reset_calls(connect, first, second)
        repo = PostgresTranscriptSegmentRepository(connect)
        await repo.record(TranscriptEvent(call_id=first, segment_id=1, speaker="customer",
                                          text=MASKED, is_final=True, utterance_end_ms=2600,
                                          masked=(MaskedSpan(type="P4", span=(6, 17)),)))
        await repo.record(TranscriptEvent(call_id=second, segment_id=1, speaker="customer",
                                          text="수도요금이 왜 이래요", is_final=True, utterance_end_ms=1800))
        # 같은 통화의 같은 발화를 다시 받으면 교체된다 — 행이 늘지 않는다
        await repo.record(TranscriptEvent(call_id=second, segment_id=1, speaker="customer",
                                          text="수도요금이 왜 이렇게 나왔어요", is_final=True, utterance_end_ms=2100))

        query = PostgresTranscriptQueryRepository(connect)
        return await query.list_segments(first, 10, 0), await query.list_segments(second, 10, 0)

    first_rows, second_rows = asyncio.run(scenario())

    assert [(e.segment_id, e.text) for e in first_rows] == [(1, MASKED)]
    assert first_rows[0].masked == (MaskedSpan(type="P4", span=(6, 17)),)
    assert [(e.segment_id, e.text) for e in second_rows] == [(1, "수도요금이 왜 이렇게 나왔어요")]
    assert second_rows[0].masked == ()  # 다른 통화의 같은 순번 구간이 섞이지 않는다


async def _reset_calls(connect, *call_ids):
    """FK 때문에 call 이 먼저 있어야 한다. 지난 실행이 남긴 행은 자식부터 지운다."""
    async with connect() as conn:
        async with conn.cursor() as cur:
            for call_id in call_ids:
                await cur.execute("DELETE FROM masking_event WHERE call_id=%s", (call_id,))
                await cur.execute("DELETE FROM transcript_segment WHERE call_id=%s", (call_id,))
                await cur.execute('DELETE FROM "call" WHERE call_id=%s', (call_id,))
                await cur.execute(
                    'INSERT INTO "call" (call_id, domain, started_at, channel_count, stt_engine, status)'
                    " VALUES (%s,'dasan',NOW(),1,'google-stt','closed')",
                    (call_id,),
                )
        await conn.commit()
