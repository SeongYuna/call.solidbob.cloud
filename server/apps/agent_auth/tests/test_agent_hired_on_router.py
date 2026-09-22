# Requirement: J-5, QUA-1
"""PUT /admin/agents/{agent_id}/hired-on — 관리자가 상담원 입사일을 넣는다(`decisions/321`).

입사일을 넣는 길이 없어서 운영의 모든 상담원이 근속 0년이었다 — J-5 가 베테랑을 한 명도 고를 수 없었다.
"""

from datetime import date

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


def test_입사일을_넣으면_그_상담원을_입사일과_함께_돌려준다():
    port = FakeAgentDirectory({"agent-1": "김민준"})
    with _client(port) as c:
        r = c.put("/admin/agents/agent-1/hired-on", json={"hired_on": "2019-03-02"})
    assert r.status_code == 200
    assert r.json() == {"agent_id": "agent-1", "display_name": "김민준", "hired_on": "2019-03-02"}
    assert port.hired["agent-1"] == date(2019, 3, 2)


def test_null_이면_입사일을_지운다():
    port = FakeAgentDirectory({"agent-1": "김민준"})
    port.hired["agent-1"] = date(2019, 3, 2)
    with _client(port) as c:
        r = c.put("/admin/agents/agent-1/hired-on", json={"hired_on": None})
    assert r.status_code == 200 and r.json()["hired_on"] is None
    assert port.hired["agent-1"] is None


def test_없는_상담원은_404다():
    with _client(FakeAgentDirectory()) as c:
        assert c.put("/admin/agents/nobody/hired-on", json={"hired_on": "2019-03-02"}).status_code == 404


def test_미래_날짜는_422다():
    with _client(FakeAgentDirectory({"agent-1": "김민준"})) as c:
        assert c.put("/admin/agents/agent-1/hired-on", json={"hired_on": "2999-01-01"}).status_code == 422


def test_날짜_형식이_아니면_422다():
    with _client(FakeAgentDirectory({"agent-1": "김민준"})) as c:
        assert c.put("/admin/agents/agent-1/hired-on", json={"hired_on": "7년"}).status_code == 422


def test_관리자_로그인_없으면_401이다():
    with _client(FakeAgentDirectory({"agent-1": "김민준"}), admin=False) as c:
        assert c.put("/admin/agents/agent-1/hired-on", json={"hired_on": "2019-03-02"}).status_code == 401


def test_PostgreSQL_미설정이면_501이다():
    app.dependency_overrides[require_admin] = lambda: ADMIN
    with TestClient(app) as c:
        assert c.put("/admin/agents/agent-1/hired-on", json={"hired_on": "2019-03-02"}).status_code == 501


def test_목록에도_입사일이_실린다():
    """관리자 화면이 지금 값을 보여 주려면 목록에 있어야 한다. 없으면 null."""
    port = FakeAgentDirectory({"agent-1": "김민준", "agent-7": "홍길동"})
    port.hired["agent-7"] = date(2018, 1, 5)
    with _client(port) as c:
        agents = c.get("/admin/agents").json()["agents"]
    assert {a["agent_id"]: a["hired_on"] for a in agents} == {"agent-1": None, "agent-7": "2018-01-05"}
