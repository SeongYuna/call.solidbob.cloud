# Requirement: J-1, QUA-1
"""GET /admin/agents — 토큰 발급 화면이 ID 대신 이름으로 상담원을 고르는 자리."""

from fastapi.testclient import TestClient

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.ports.input.current_admin_use_case import CurrentAdminUseCase
from admin_auth.dependencies.use_case_providers import get_current_admin_use_case
from agent_auth.dependencies.providers import get_agent_directory_port
from main import app

from ._fakes import FakeAgentDirectory

ADMIN = AdminAccount(id=3, email="admin@example.com", name="관리자", agent_id=None)


class _NoSession(CurrentAdminUseCase):
    async def current(self, access_token):
        return None


def _client(port, admin=True):
    app.dependency_overrides[get_agent_directory_port] = lambda: port
    if admin:
        app.dependency_overrides[require_admin] = lambda: ADMIN
    else:
        app.dependency_overrides[get_current_admin_use_case] = lambda: _NoSession()
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_관리자_로그인_없으면_401이다():
    with _client(FakeAgentDirectory(), admin=False) as c:
        assert c.get("/admin/agents").status_code == 401


def test_이름순으로_정렬돼_돌아온다():
    port = FakeAgentDirectory({"agent-7": "홍길동", "agent-1": "김민준"})
    with _client(port) as c:
        r = c.get("/admin/agents")
    assert r.status_code == 200
    assert r.json() == {
        "agents": [
            {"agent_id": "agent-1", "display_name": "김민준"},
            {"agent_id": "agent-7", "display_name": "홍길동"},
        ]
    }


def test_아무도_없으면_빈_목록이다():
    with _client(FakeAgentDirectory()) as c:
        assert c.get("/admin/agents").json() == {"agents": []}


def test_PostgreSQL_미설정이면_501이다():
    app.dependency_overrides[require_admin] = lambda: ADMIN
    with TestClient(app) as c:
        assert c.get("/admin/agents").status_code == 501
