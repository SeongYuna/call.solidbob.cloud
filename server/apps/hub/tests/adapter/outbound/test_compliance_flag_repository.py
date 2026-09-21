# Requirement: C-1, C-2, C-3, C-4, D-4, SEC-1, QUA-1
"""컴플라이언스 위반 저장. 가짜 커넥션으로 모양을, `@pytest.mark.integration` 으로 실제 스키마를 본다."""

import asyncio
from contextlib import asynccontextmanager

import pytest

from hub.adapter.outbound.postgres.compliance_flag_repository import (
    COMPLIANCE_RULE_CATALOG,
    PostgresComplianceFlagRepository,
)
from hub.app.dtos import ComplianceFinding, Source
from hub.app.ports.output.transcript_ingest_record_port import SegmentNotFoundError

FINDING = ComplianceFinding(rule_code="C-1", phrase="무조건 됩니다",
                            alternative_source=Source(doc_id="DASAN-MANUAL-1.4", title="권장 대체 표현"))


class _FkViolation(Exception):
    sqlstate = "23503"


class _FakeCursor:
    def __init__(self, log, fail_insert=False):
        self._log = log
        self._fail_insert = fail_insert

    async def executemany(self, sql, rows):
        flat = " ".join(sql.split())
        self._log.append(("executemany", flat, rows))
        if self._fail_insert and 'INSERT INTO "compliance_flag"' in flat:
            raise _FkViolation()


class _FakeConnection:
    def __init__(self, log, fail_insert):
        self._log = log
        self._fail_insert = fail_insert

    @asynccontextmanager
    async def cursor(self):
        yield _FakeCursor(self._log, self._fail_insert)

    async def commit(self):
        self._log.append(("commit", "", None))


def _repo(log, fail_insert=False):
    @asynccontextmanager
    async def connect():
        yield _FakeConnection(log, fail_insert)

    return PostgresComplianceFlagRepository(connect)


def test_카탈로그를_먼저_채우고_위반마다_한_행을_넣고_커밋한다():
    log = []
    asyncio.run(_repo(log).record("c_001", 7, (FINDING, FINDING)))
    kind, sql, rows = log[0]
    assert kind == "executemany" and 'INSERT INTO "compliance_rule"' in sql and "ON CONFLICT" in sql
    assert rows == [("C-1", *COMPLIANCE_RULE_CATALOG["C-1"])]
    kind, sql, rows = log[1]
    assert kind == "executemany" and 'INSERT INTO "compliance_flag"' in sql
    assert [r[:4] for r in rows] == [("c_001", 7, "C-1", "무조건 됩니다")] * 2
    assert log[-1][0] == "commit"


def test_카탈로그는_네_코드_전부이고_등급을_가르지_않는다():
    """`default_severity` 는 등급 정의가 없어 전부 같은 값이다(부록 A-1) — 누가 값을 갈라 넣으면 여기서 드러난다."""
    assert set(COMPLIANCE_RULE_CATALOG) == {"C-1", "C-2", "C-3", "C-4"}
    assert len({severity for _, severity, _ in COMPLIANCE_RULE_CATALOG.values()}) == 1


def test_카탈로그_밖_코드는_저장하지_않는다():
    log = []
    with pytest.raises(RuntimeError):
        asyncio.run(_repo(log).record("c_001", 7, (ComplianceFinding(rule_code="C-9", phrase="x"),)))
    assert log == []


def test_전사가_없으면_SegmentNotFoundError_다():
    """통화는 있는데 **전사 구간**이 없는 것이다 — 전에는 `CallNotStartedError`(「통화가 없다」)로 올려 이름이 틀렸다.

    2026-09-20 운영 왕복에서 이 상황이 응답 200 + 조용한 저장 실패로 나왔다. 어느 구간인지까지 싣는다.
    """
    log = []
    with pytest.raises(SegmentNotFoundError) as caught:
        asyncio.run(_repo(log, fail_insert=True).record("c_001", 7, (FINDING,)))
    assert (caught.value.call_id, caught.value.segment_id) == ("c_001", 7)
    assert log[-1][0] != "commit"


def test_너무_긴_표현은_컬럼_길이로_자른다():
    log = []
    asyncio.run(_repo(log).record("c_001", 7, (ComplianceFinding(rule_code="C-1", phrase="가" * 250),)))
    assert len(log[1][2][0][3]) == 200


@pytest.mark.integration
def test_실제_DB에_위반이_전사를_참조해_저장된다(integration_settings):
    from hub.adapter.outbound.postgres.connection import build_connection_factory
    from hub.adapter.outbound.postgres.transcript_segment_repository import PostgresTranscriptSegmentRepository
    from hub.app.dtos import TranscriptEvent

    connect = build_connection_factory(integration_settings)
    call_id = "it_c1_001"

    async def scenario():
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM compliance_flag WHERE call_id=%s", (call_id,))
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
            TranscriptEvent(call_id=call_id, segment_id=3, speaker="agent", text="무조건 됩니다", is_final=True)
        )
        await PostgresComplianceFlagRepository(connect).record(call_id, 3, (FINDING,))
        # 전사가 없는 발화에 붙이면 외래키 — SegmentNotFoundError
        try:
            await PostgresComplianceFlagRepository(connect).record(call_id, 99, (FINDING,))
            missing = None
        except SegmentNotFoundError as exc:
            missing = exc
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT rule_code, phrase, confidence FROM compliance_flag WHERE call_id=%s", (call_id,)
                )
                rows = await cur.fetchall()
                await cur.execute("SELECT count(*) FROM compliance_rule WHERE rule_code='C-1'")
                catalog = (await cur.fetchone())[0]
        return rows, catalog, missing

    rows, catalog, missing = asyncio.run(scenario())
    assert rows == [("C-1", "무조건 됩니다", None)]
    assert catalog == 1
    assert missing is not None
