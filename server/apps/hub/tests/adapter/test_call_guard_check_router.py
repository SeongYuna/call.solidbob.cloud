# Requirement: C-6, QUA-1
"""HTTP 표면: 스포크가 없으면 501, 있으면 값은 전부 문자열로."""

from fastapi.testclient import TestClient

from hub.app.dtos.call_guard_dto import CallGuardFlag
from hub.app.ports.output.call_guard_port import CallGuardPort
from hub.dependencies.call_guard_provider import get_call_guard_port
from main import app

BODY = {"call_id": "c_001", "segment_id": 7, "customer_utterance": "이런 병신 같은"}


class _Stub(CallGuardPort):
    async def detect(self, customer_utterance):
        return [CallGuardFlag(category="insult", phrase="병신", source_doc_id="DASAN-MANUAL-5.1", span=(3, 5))]


def test_스포크가_없으면_501이다(monkeypatch):
    """빈 목록으로 200 을 주면 '탐지가 꺼진 것'이 '폭언 없음'으로 읽힌다."""
    import main

    monkeypatch.setattr(main, "_wire_call_guard", lambda app: None)
    app.dependency_overrides.pop(get_call_guard_port, None)
    with TestClient(app) as client:
        r = client.post("/hub/call-guard-checks", json=BODY)
    assert r.status_code == 501


def test_잡힌_신호를_문자열_값으로_돌려준다():
    app.dependency_overrides[get_call_guard_port] = lambda: _Stub()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/call-guard-checks", json=BODY)
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json() == {
        "call_id": "c_001",
        "segment_id": "7",
        "flags": [{"category": "insult", "phrase": "병신", "span": ["3", "5"], "source_doc_id": "DASAN-MANUAL-5.1"}],
    }


def test_빈_발화는_422다():
    app.dependency_overrides[get_call_guard_port] = lambda: _Stub()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/call-guard-checks", json={**BODY, "customer_utterance": "  "})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 422
