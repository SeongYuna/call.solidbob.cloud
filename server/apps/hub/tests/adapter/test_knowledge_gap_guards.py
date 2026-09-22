# Requirement: D-4, SEC-1, QUA-1
"""지식 공백의 문(`_project/decisions/322`) — 조회·집계·상태 변경은 관리자, 신고는 상담원.

관리자 화면은 이미 관리자 토큰을 싣는다(`apps/admin` `authedGet`·`authedPatch`). 신고는 부르는 곳이 아직 없다.
그래서 이 둘은 이행기 없이 바로 닫는다. 설명은 마스킹한 뒤 저장한다.
"""

import pytest
from fastapi.testclient import TestClient

from admin_auth.app.ports.input.current_admin_use_case import CurrentAdminUseCase
from admin_auth.dependencies.use_case_providers import get_current_admin_use_case
from agent_auth.app.ports.input.current_agent_use_case import CurrentAgentUseCase
from agent_auth.dependencies.use_case_providers import get_current_agent_use_case
from main import app


class _NoAdmin(CurrentAdminUseCase):
    async def current(self, access_token):
        return None


class _NoAgent(CurrentAgentUseCase):
    async def current(self, token):
        return None


def teardown_function():
    app.dependency_overrides.clear()


@pytest.mark.parametrize("method, path, body", [
    ("get", "/hub/knowledge-gaps", None),
    ("get", "/hub/knowledge-gaps/summary", None),
    ("patch", "/hub/knowledge-gaps/1", {"status": "resolved"}),
])
def test_조회_집계_상태변경은_관리자_토큰이_없으면_401이다(method, path, body):
    app.dependency_overrides[get_current_admin_use_case] = lambda: _NoAdmin()
    with TestClient(app) as c:
        res = getattr(c, method)(path, **({"json": body} if body else {}))
        assert res.status_code == 401
        res = getattr(c, method)(path, headers={"Authorization": "Bearer wrong"}, **({"json": body} if body else {}))
        assert res.status_code == 401


def test_신고는_상담원_토큰이_없으면_401이다():
    app.dependency_overrides[get_current_agent_use_case] = lambda: _NoAgent()
    with TestClient(app) as c:
        assert c.post("/hub/knowledge-gaps", json={"module": "B", "description": "못 찾음"}).status_code == 401
        assert c.post("/hub/knowledge-gaps", json={"module": "B", "description": "못 찾음"},
                      headers={"Authorization": "Bearer cga_wrong"}).status_code == 401
