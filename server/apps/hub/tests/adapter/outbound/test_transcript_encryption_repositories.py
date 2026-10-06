# Requirement: C-5, SEC-1, SEC-2, QUA-1
"""전사 본문 암호화(`decisions/326`) — 쓰는 곳 하나, 읽는 곳 둘이 같은 암호화기로 맞물리는지 가짜 커넥션으로 본다.

실제 PostgreSQL 왕복은 `test_transcript_encryption_integration.py`(integration 마커)가 본다.
"""

import asyncio
import base64
from contextlib import asynccontextmanager

from hub.adapter.outbound.postgres.blacklist_evidence_repository import (
    EXCERPT_MAX_CHARS,
    PostgresBlacklistEvidenceRepository,
)
from hub.adapter.outbound.postgres.transcript_query_repository import PostgresTranscriptQueryRepository
from hub.adapter.outbound.postgres.transcript_segment_repository import PostgresTranscriptSegmentRepository
from hub.adapter.outbound.transcript_text_cipher import TranscriptTextCipher
from hub.app.dtos import MaskedSpan, TranscriptEvent

CIPHER = TranscriptTextCipher(base64.b64encode(bytes(range(32))).decode("ascii"))
MASKED = "제 번호는 *********** 입니다"


class _Cursor:
    """execute 를 기록하고, 미리 준 결과를 차례로 fetch 로 돌려준다."""

    def __init__(self, log: list, results: list):
        self._log = log
        self._results = results

    async def execute(self, sql, args=None):
        self._log.append((" ".join(sql.split()), args))
        return self

    async def executemany(self, sql, args):
        self._log.append((" ".join(sql.split()), args))

    async def fetchall(self):
        return self._results.pop(0)

    async def fetchone(self):
        rows = self._results.pop(0)
        return rows[0] if rows else None


def _factory(log: list, results: list | None = None):
    class _Conn:
        @asynccontextmanager
        async def cursor(self):
            yield _Cursor(log, results if results is not None else [])

        async def commit(self):
            log.append(("commit", None))

    @asynccontextmanager
    async def _connect():
        yield _Conn()

    return _connect


def _event() -> TranscriptEvent:
    return TranscriptEvent(call_id="c_001", segment_id=3, speaker="customer", text=MASKED, is_final=True,
                           utterance_end_ms=1200, masked=(MaskedSpan(type="P4", span=(6, 17)),))


def test_저장할_때_마스킹본을_암호문으로_넣는다():
    log: list = []
    asyncio.run(PostgresTranscriptSegmentRepository(_factory(log), cipher=CIPHER).record(_event()))
    stored = log[0][1][3]  # INSERT 의 text 자리
    assert stored.startswith(TranscriptTextCipher.PREFIX)
    assert MASKED not in stored
    assert CIPHER.unseal(stored) == MASKED
    # 마스킹 구간은 위치·패턴뿐이라 그대로 들어간다
    assert log[2][1] == [("c_001", 3, "P4", 6, 17, log[2][1][0][5])]


def test_암호화기를_안_주면_지금처럼_마스킹본_평문이다():
    log: list = []
    asyncio.run(PostgresTranscriptSegmentRepository(_factory(log)).record(_event()))
    assert log[0][1][3] == MASKED


def test_지난_통화_보기는_풀어서_마스킹본으로_돌려준다():
    sealed = CIPHER.seal(MASKED)
    results = [
        [(3, "customer", sealed, True, 1200), (4, "agent", "평문으로 남은 옛 행", True, 1800)],
        [(3, "P4", 6, 17)],
    ]
    repo = PostgresTranscriptQueryRepository(_factory([], results), cipher=CIPHER)
    segments = asyncio.run(repo.list_segments("c_001", limit=10, offset=0))
    assert [s.text for s in segments] == [MASKED, "평문으로 남은 옛 행"]
    assert segments[0].masked == (MaskedSpan(type="P4", span=(6, 17)),)


def test_블랙리스트_근거는_풀고_나서_자른다():
    """암호문을 먼저 자르면 못 푼다 — 그리고 길이 제한은 사람이 읽는 글자 기준이어야 한다."""
    long_text = "가" * (EXCERPT_MAX_CHARS + 50)
    results = [
        [("cust_1", 30.0, "****5678")],  # 통화
        [],  # 콜 가드 건수
        [(CIPHER.seal(long_text),)],  # 콜 가드가 잡힌 고객 발화
    ]
    repo = PostgresBlacklistEvidenceRepository(_factory([], results), cipher=CIPHER)
    evidence = asyncio.run(repo.collect("c_001"))
    assert evidence.context_excerpt == "가" * EXCERPT_MAX_CHARS


def test_쓰는_곳과_읽는_곳_프로바이더가_같은_키를_넘긴다():
    """한쪽만 키를 보면 쓴 것을 못 읽거나 평문으로 쓴다 — 세 프로바이더를 설정 하나로 만든다."""
    from types import SimpleNamespace

    from hub.dependencies.blacklist_provider import get_blacklist_evidence_port
    from hub.dependencies.transcript_query_provider import get_transcript_query_port
    from hub.dependencies.transcript_record_provider import get_transcript_record_port

    key = base64.b64encode(bytes(range(32))).decode("ascii")
    settings = SimpleNamespace(postgres_configured=True, database_url="postgresql://u:p@db:5432/x",
                               transcript_enc_key=key)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)))

    ports = [get_transcript_record_port(request), get_transcript_query_port(request),
             get_blacklist_evidence_port(request)]
    sealed = ports[0]._cipher.seal(MASKED)
    assert all(p._cipher.enabled for p in ports)
    assert ports[1]._cipher.unseal(sealed) == MASKED
    assert ports[2]._cipher.unseal(sealed) == MASKED
