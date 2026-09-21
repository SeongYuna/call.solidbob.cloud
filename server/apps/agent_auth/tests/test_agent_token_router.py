# Requirement: J-1, SEC-1, QUA-1
"""HTTP 표면: 관리자만 발급·조회·폐기 · 원문 토큰은 발급 응답에만 · DB 없으면 501.
모르는 이름으로 발급하면 그 자리에서 상담원이 만들어진다(`decisions/406`)."""

from fastapi.testclient import TestClient

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.ports.input.current_admin_use_case import CurrentAdminUseCase
from admin_auth.dependencies.use_case_providers import get_current_admin_use_case
from agent_auth.dependencies.providers import get_agent_directory_port, get_agent_token_port
from main import app

from ._fakes import FakeAgentDirectory, FakeAgentTokens

ADMIN = AdminAccount(id=3, email="admin@example.com", name="관리자", agent_id=None)


class _NoSession(CurrentAdminUseCase):
    """세션 없는 관리자 — 실제 가드가 401 을 내는지 본다. Redis 없이 돈다."""

    async def current(self, access_token):
        return None


def _client(port, admin=True, agents=None):
    app.dependency_overrides[get_agent_token_port] = lambda: port
    app.dependency_overrides[get_agent_directory_port] = lambda: (
        agents if agents is not None else FakeAgentDirectory({"agent-7": "agent-7"})
    )
    if admin:
        app.dependency_overrides[require_admin] = lambda: ADMIN
    else:
        app.dependency_overrides[get_current_admin_use_case] = lambda: _NoSession()
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_관리자_로그인_없으면_401이다():
    with _client(FakeAgentTokens(), admin=False) as c:
        assert c.post("/admin/agent-tokens", json={"agent_id": "agent-7"}).status_code == 401
        assert c.get("/admin/agent-tokens").status_code == 401
        assert c.post("/admin/agent-tokens/1/revoke").status_code == 401


def test_발급_응답에만_원문_토큰이_있다():
    port = FakeAgentTokens()
    with _client(port) as c:
        issued = c.post("/admin/agent-tokens", json={"agent_id": "agent-7"})
        listed = c.get("/admin/agent-tokens")
    assert issued.status_code == 201
    body = issued.json()
    assert body["token"].startswith("cga_")
    assert body["item"] == {"id": "1", "agent_id": "agent-7", "issued_by": "3",
                            "issued_at": "2026-09-15T12:00:00+00:00", "revoked_at": None}
    assert body["token"] not in listed.text and port.rows[0]["token_hash"] not in listed.text
    assert listed.json()["tokens"][0]["agent_id"] == "agent-7"


def test_모르는_이름은_새로_만들어_발급한다():
    directory = FakeAgentDirectory()
    with _client(FakeAgentTokens(agents=None), agents=directory) as c:
        r = c.post("/admin/agent-tokens", json={"agent_id": "nobody"})
    assert r.status_code == 201
    assert r.json()["item"]["agent_id"] == "nobody"  # agent_id 는 이름 그대로 쓴다


def test_없는_토큰_폐기는_404다():
    with _client(FakeAgentTokens()) as c:
        assert c.post("/admin/agent-tokens/99/revoke").status_code == 404


def test_폐기하면_폐기_시각이_찍힌다():
    port = FakeAgentTokens()
    with _client(port) as c:
        c.post("/admin/agent-tokens", json={"agent_id": "agent-7"})
        r = c.post("/admin/agent-tokens/1/revoke")
    assert r.status_code == 200 and r.json()["revoked_at"] == "2026-09-15T12:00:00+00:00"


def test_PostgreSQL_미설정이면_501이다():
    app.dependency_overrides[require_admin] = lambda: ADMIN
    with TestClient(app) as c:
        assert c.post("/admin/agent-tokens", json={"agent_id": "agent-7"}).status_code == 501
