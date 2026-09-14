# Requirement: B-1, B-2, QUA-1
"""합성 루트의 배선 — 트리거 스포크가 꽂히는지, 인덱스가 없을 때 500 이 아니라 503 인지."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from main import AI_APPS, app

ES_AVAILABLE = importlib.util.find_spec("elasticsearch") is not None


def _ai_provider_available() -> bool:
    sys.path.insert(0, str(AI_APPS)); sys.path.insert(0, str(AI_APPS.parent))
    return importlib.util.find_spec("provider") is not None and Path(AI_APPS).exists()


@pytest.mark.skipif(not _ai_provider_available(), reason="ai/ 가 없다 — 트리거 스포크가 안 꽂힌다")
def test_트리거_스포크가_꽂힌다():
    """`w3-trigger-v1` 이 남긴 배선 — 마지막 501 이 여기서 풀린다."""
    with TestClient(app) as client:
        assert "trigger" in client.get("/health").json()["spokes"]


@pytest.mark.skipif(not _ai_provider_available(), reason="ai/ 가 없다")
def test_트리거가_꽂히면_추천이_501이_아니다(monkeypatch):
    """트리거는 꽂혔고 검색은 없다 → 501 의 원인이 검색으로 옮겨간다(임시 통과 없음)."""
    monkeypatch.delenv("ELASTICSEARCH_URL", raising=False)
    body = {"call_id": "test-c001", "segment_id": 1, "speaker": "customer", "text": "여권 재발급 서류가 뭐예요",
            "is_final": True, "utterance_end_ms": 1000}
    with TestClient(app) as client:
        r = client.post("/hub/recommendations", json=body)
    assert r.status_code == 501
    assert "retrieval" in r.json()["detail"]


@pytest.mark.skipif(not ES_AVAILABLE, reason="elasticsearch 패키지 없음")
def test_인덱스가_없으면_503이고_이유를_말한다():
    """운영에서 적재 전에 500 이 났던 것 — 코드 오류가 아니라 적재 미완이라고 답한다."""
    from elasticsearch import NotFoundError

    from hub.app.ports.output import RetrievalPort
    from hub.dependencies.retrieval_provider import get_retrieval_port

    class _NoIndex(RetrievalPort):
        async def retrieve(self, utterance: str, top_k: int = 5):
            raise NotFoundError("index_not_found_exception", meta=SimpleNamespace(status=404), body={})

    app.dependency_overrides[get_retrieval_port] = lambda: _NoIndex()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/search", json={"utterance": "여권 재발급"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert "적재" in r.json()["detail"]


@pytest.mark.skipif(not ES_AVAILABLE, reason="elasticsearch 패키지 없음")
@pytest.mark.parametrize("error_name", ["ConnectionError", "ConnectionTimeout"])
def test_ES_에_연결하지_못하면_503이고_주소를_싣지_않는다(error_name):
    """로컬에 ES 가 없을 때 500 이었다 (w4-es-unreachable-503). 예외 메시지의 주소는 밖에 내지 않는다(SEC-2)."""
    import elasticsearch

    from hub.app.ports.output import RetrievalPort
    from hub.dependencies.retrieval_provider import get_retrieval_port

    error = getattr(elasticsearch, error_name)

    class _Unreachable(RetrievalPort):
        async def retrieve(self, utterance: str, top_k: int = 5):
            raise error("http://secret-es.internal:9200 refused")

    app.dependency_overrides[get_retrieval_port] = lambda: _Unreachable()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/search", json={"utterance": "여권 재발급"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert "연결" in r.json()["detail"]
    assert "secret-es" not in r.text


@pytest.mark.skipif(not _ai_provider_available(), reason="ai/ 가 없다 — 콜 가드가 안 꽂힌다")
def test_콜_가드가_전사_수신에_꽂혀_마스킹된_구간만_기록한다():
    """C-6 · MANUAL-5.5 — 실제 마스킹(server)과 실제 콜 가드(ai)를 합성 루트에서 함께 돌린다.
    기록 포트만 스파이로 바꾼다(DB 없이)."""
    from hub.app.ports.output import CallGuardRecordPort, TranscriptIngestRecordPort
    from hub.dependencies.call_guard_provider import get_call_guard_record_port
    from hub.dependencies.transcript_record_provider import get_transcript_record_port

    saved_text: list[str] = []
    saved_flags: list = []

    class _Segments(TranscriptIngestRecordPort):
        async def record(self, event):
            saved_text.append(event.text)

    class _Flags(CallGuardRecordPort):
        async def replace(self, call_id, segment_id, flags):
            saved_flags.extend(flags)

    app.dependency_overrides[get_transcript_record_port] = lambda: _Segments()
    app.dependency_overrides[get_call_guard_record_port] = lambda: _Flags()
    body = {"call_id": "test-c6", "segment_id": 1, "speaker": "customer", "is_final": True,
            "text": "제 번호는 01012345678 이고 이 개새끼야 가만 안 둬"}
    with TestClient(app) as client:
        assert "call_guard" in client.get("/health").json()["spokes"]
        r = client.post("/hub/transcripts", json=body)

    assert r.status_code == 200, r.text
    [text] = saved_text
    assert "01012345678" not in text
    assert {f.category for f in saved_flags} >= {"insult", "threat"}
    for f in saved_flags:
        assert text[f.span_start:f.span_end] == f.phrase
        assert not any(ch.isdigit() for ch in f.phrase)
