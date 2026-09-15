# Requirement: J-1, J-2, QUA-1
"""HTTP 표면: 상담원 토큰 필수(decisions/307) · DB 없으면 501 · 값은 문자열 · 고객 미식별 409 · 통화 없음 404."""

from fastapi.testclient import TestClient

from agent_auth.dependencies.providers import get_agent_token_port
from agent_auth.tests._fakes import FakeAgentTokens
from hub.dependencies.blacklist_provider import get_blacklist_evidence_port, get_blacklist_port
from hub.tests.app.use_cases._blacklist_stubs import StubBlacklist, StubEvidence, evidence
from main import app

TOKEN = "cga_test-token-for-agent-7"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
BODY = {"call_id": "c1", "reason": "반복 폭언"}


def _tokens():
    port = FakeAgentTokens()
    port.seed("agent-7", TOKEN)
    return port


def _post(collected, body=BODY, headers=AUTH):
    blacklist = StubBlacklist()
    app.dependency_overrides[get_agent_token_port] = _tokens
    app.dependency_overrides[get_blacklist_port] = lambda: blacklist
    app.dependency_overrides[get_blacklist_evidence_port] = lambda: StubEvidence(collected)
    try:
        with TestClient(app) as client:
            return client.post("/hub/blacklist-requests", json=body, headers=headers), blacklist
    finally:
        app.dependency_overrides.clear()


def test_PostgreSQL_미설정이면_501이다():
    with TestClient(app) as client:
        assert client.post("/hub/blacklist-requests", json=BODY, headers=AUTH).status_code == 501


def test_요청을_만들고_값은_문자열로_돌려준다():
    r, _ = _post(evidence(distress=1))
    assert r.status_code == 201
    b = r.json()
    assert b["has_distress"] == "true"
    assert b["request"]["status"] == "pending" and b["request"]["request_id"] == "7"
    assert b["request"]["evidence"]["insult_count"] == "3"
    assert "distress_count" not in b["request"]["evidence"]  # 저장되지 않는 값은 항목에 없다


def test_고객이_식별되지_않은_통화는_409_없는_통화는_404():
    assert _post(evidence(customer_ref=None))[0].status_code == 409
    assert _post(None)[0].status_code == 404


def test_토큰이_없거나_틀리면_401이다():
    assert _post(evidence(), headers={})[0].status_code == 401
    assert _post(evidence(), headers={"Authorization": "Bearer cga_wrong"})[0].status_code == 401


def test_요청자는_본문이_아니라_토큰에서_온다():
    """본문에 남의 ID 를 실어도 저장되는 요청자는 토큰의 상담원이다 — decisions/304 의 남은 구멍."""
    r, blacklist = _post(evidence(), body={**BODY, "requested_by": "someone-else"})
    assert r.status_code == 201
    (_, saved), = blacklist.calls
    assert saved.requested_by == "agent-7"
    assert r.json()["request"]["requested_by"] == "agent-7"


def test_헤더가_없으면_DB_설정이_없어도_501이_아니라_401이다():
    """헤더 검사가 저장소 의존성(DB 없으면 501)보다 먼저다 — 누가 불렀는지 모르면 인프라를 보기 전에 끊는다."""
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        assert client.post("/hub/blacklist-requests", json=BODY).status_code == 401
