# Requirement: J-1, QUA-1
"""GET /hub/agents/me — 로그인 화면이 토큰을 검증하는 자리. 판정은 `require_agent`가 다 하므로
여기서는 그 결과(401·501·통과)가 그대로 나오는지만 본다."""

from fastapi.testclient import TestClient

from agent_auth.dependencies.providers import get_agent_token_port
from main import app

from ._fakes import FakeAgentTokens


def _client(port):
    app.dependency_overrides[get_agent_token_port] = lambda: port
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_유효한_토큰이면_agent_id를_돌려준다():
    port = FakeAgentTokens()
    port.seed("agent-7", "cga_valid")
    with _client(port) as c:
        r = c.get("/hub/agents/me", headers={"Authorization": "Bearer cga_valid"})
    assert r.status_code == 200
    assert r.json() == {"agent_id": "agent-7"}


def test_토큰_없으면_401이다():
    with _client(FakeAgentTokens()) as c:
        assert c.get("/hub/agents/me").status_code == 401


def test_폐기된_토큰이면_401이다():
    port = FakeAgentTokens()
    port.seed("agent-7", "cga_revoked")
    port.rows[0]["revoked_at"] = port.rows[0]["issued_at"]
    with _client(port) as c:
        r = c.get("/hub/agents/me", headers={"Authorization": "Bearer cga_revoked"})
    assert r.status_code == 401


def test_PostgreSQL_미설정이면_501이다():
    with TestClient(app) as c:
        r = c.get("/hub/agents/me", headers={"Authorization": "Bearer cga_anything"})
    assert r.status_code == 501
