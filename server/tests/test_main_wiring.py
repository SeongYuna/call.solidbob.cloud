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
