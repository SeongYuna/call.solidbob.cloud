# Requirement: J-1, J-2, QUA-1
"""HTTP 표면: DB 없으면 501 · 값은 문자열 · 고객 미식별 409 · 통화 없음 404."""

from fastapi.testclient import TestClient

from hub.dependencies.blacklist_provider import get_blacklist_evidence_port, get_blacklist_port
from hub.tests.app.use_cases._blacklist_stubs import StubBlacklist, StubEvidence, evidence
from main import app

BODY = {"call_id": "c1", "requested_by": "agent-7", "reason": "반복 폭언"}


def _post(collected):
    app.dependency_overrides[get_blacklist_port] = lambda: StubBlacklist()
    app.dependency_overrides[get_blacklist_evidence_port] = lambda: StubEvidence(collected)
    try:
        with TestClient(app) as client:
            return client.post("/hub/blacklist-requests", json=BODY)
    finally:
        app.dependency_overrides.clear()


def test_PostgreSQL_미설정이면_501이다():
    with TestClient(app) as client:
        assert client.post("/hub/blacklist-requests", json=BODY).status_code == 501


def test_요청을_만들고_값은_문자열로_돌려준다():
    r = _post(evidence(distress=1))
    assert r.status_code == 201
    b = r.json()
    assert b["has_distress"] == "true"
    assert b["request"]["status"] == "pending" and b["request"]["request_id"] == "7"
    assert b["request"]["evidence"]["insult_count"] == "3"
    assert "distress_count" not in b["request"]["evidence"]  # 저장되지 않는 값은 항목에 없다


def test_고객이_식별되지_않은_통화는_409_없는_통화는_404():
    assert _post(evidence(customer_ref=None)).status_code == 409
    assert _post(None).status_code == 404
