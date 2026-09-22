# Requirement: J-2, J-4, QUA-1
"""GET /hub/blacklist-requests/mine — 토큰 없음·틀림 401 · 요청자는 토큰에서만 · 응답에 HMAC·결정자·근거가 없다."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from agent_auth.app.ports.input.current_agent_use_case import CurrentAgentUseCase
from agent_auth.dependencies.use_case_providers import get_current_agent_use_case
from hub.app.dtos.blacklist_dto import BlacklistRequest
from hub.dependencies.blacklist_provider import get_blacklist_port
from hub.tests.app.use_cases._blacklist_stubs import StubBlacklist
from main import app

T = datetime(2026, 9, 22, 3, 0, tzinfo=timezone.utc)


class _Agents(CurrentAgentUseCase):
    async def current(self, token):
        return "a_01" if token == "cga_good" else None


class _Mine(StubBlacklist):
    async def list_requests(self, status=None, requested_by=None):
        self.calls.append(("list_requests", status, requested_by))
        return [BlacklistRequest(request_id="7", call_id="c1", customer_ref="f" * 64, requested_by=requested_by,
                                 reason="반복 폭언", context_excerpt="자막", status="rejected", requested_at=T,
                                 decided_by="admin-1", decided_at=T, decision_note="통화 기록상 폭언 아님")]


def _client(port):
    app.dependency_overrides[get_current_agent_use_case] = lambda: _Agents()
    app.dependency_overrides[get_blacklist_port] = lambda: port
    return TestClient(app)


def test_토큰이_없거나_틀리면_401이다():
    try:
        with _client(_Mine()) as c:
            assert c.get("/hub/blacklist-requests/mine").status_code == 401
            assert c.get("/hub/blacklist-requests/mine", headers={"Authorization": "Bearer cga_bad"}).status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_요청자는_토큰에서만_오고_반려_사유가_보인다():
    port = _Mine()
    try:
        with _client(port) as c:
            # 쿼리로 남의 ID 를 실어도 무시된다
            r = c.get("/hub/blacklist-requests/mine?requested_by=someone", headers={"Authorization": "Bearer cga_good"})
        assert r.status_code == 200
        assert port.calls == [("list_requests", None, "a_01")]
        (item,) = r.json()["requests"]
        assert item["status"] == "rejected" and item["decision_note"] == "통화 기록상 폭언 아님"
        assert not {"customer_ref", "decided_by", "evidence", "context_excerpt", "requested_by"} & set(item)
    finally:
        app.dependency_overrides.clear()
