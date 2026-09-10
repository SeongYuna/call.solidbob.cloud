# Requirement: B-1, B-5, B-6, QUA-1
"""HTTP 표면: trigger 스포크가 없으면 501, 있으면 계약 형태로 응답."""

from fastapi.testclient import TestClient

from hub.app.dtos import RetrievedDoc
from hub.app.dtos.trigger_decision_dto import TriggerDecision
from hub.app.ports.output import RetrievalPort, TriggerPort
from hub.dependencies.retrieval_provider import get_retrieval_port
from hub.dependencies.trigger_provider import get_trigger_port
from main import app

BODY = {"call_id": "c_001", "segment_id": 31, "speaker": "customer",
        "text": "반품 배송비는 누가 내나요", "is_final": True, "utterance_end_ms": 2600}


class _Trigger(TriggerPort):
    def __init__(self, fire=True):
        self.fire = fire

    def decide(self, event):
        return TriggerDecision(fire=self.fire, at_ms=3150 if self.fire else None)


class _Retrieval(RetrievalPort):
    async def retrieve(self, utterance, top_k=5):
        return [RetrievedDoc(doc_id="SHOP-TERM-4.1", title="반품 배송비", snippet="단순 변심은 고객 부담", score=0.91)]


def _wire(fire=True):
    app.dependency_overrides[get_trigger_port] = lambda: _Trigger(fire)
    app.dependency_overrides[get_retrieval_port] = lambda: _Retrieval()


def test_trigger_스포크가_없으면_501이다():
    with TestClient(app) as client:
        r = client.post("/hub/recommendations", json=BODY)
    assert r.status_code == 501


def test_발동하면_카드를_계약_형태로_돌려준다():
    """generation 스포크가 없어도 폴백(스니펫)으로 끝까지 돈다."""
    _wire()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/recommendations", json=BODY)
        assert r.status_code == 200
        b = r.json()
        assert b["fired"] == "true"
        assert b["trigger_at_ms"] == "3150"
        assert b["cards"][0]["source"]["doc_id"] == "SHOP-TERM-4.1"
        assert b["cards"][0]["summary"] == "단순 변심은 고객 부담"
        assert b["internal_latency_ms"] is not None
        # 7.3절 계약 필드명 — DB recommendation_card.similarity_score 와 같다 (decisions/003).
        # 이 단언이 없어서 표면이 score 로 어긋난 채 3주를 갔다.
        assert b["cards"][0]["similarity_score"] == "0.91"
        assert "score" not in b["cards"][0]
    finally:
        app.dependency_overrides.clear()


def test_미발동이면_cards가_null이다():
    """빈 배열('관련 문서 없음')과 구분된다."""
    _wire(fire=False)
    try:
        with TestClient(app) as client:
            r = client.post("/hub/recommendations", json=BODY)
        b = r.json()
        assert b["fired"] == "false" and b["cards"] is None
    finally:
        app.dependency_overrides.clear()


def test_도메인_분류기가_없으면_domain은_null이다():
    _wire()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/recommendations", json=BODY)
        assert r.json()["domain"] is None
    finally:
        app.dependency_overrides.clear()


def test_빈_텍스트는_422다():
    _wire()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/recommendations", json={**BODY, "text": ""})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()
