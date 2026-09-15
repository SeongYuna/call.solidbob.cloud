# Requirement: J-5, QUA-1
"""HTTP 표면: 배정 판정(인증 없음 — 통화 시작과 같다) · 설정(관리자) · 값은 문자열."""

from fastapi.testclient import TestClient

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from hub.app.dtos.blacklist_dto import RoutingDecision
from hub.app.dtos.routing_decision_dto import RoutedCall
from hub.app.dtos.routing_setting_dto import RoutingSetting
from hub.app.ports.output.agent_routing_port import AgentRoutingPort
from hub.app.ports.output.routing_setting_port import RoutingSettingPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.routing_decision_provider import get_agent_routing_port
from hub.dependencies.routing_setting_provider import get_routing_setting_port
from main import app

ADMIN = AdminAccount(id=5, email="a@example.com", name=None, agent_id=None)


class _Routing(AgentRoutingPort):
    def __init__(self, exc=None):
        self.exc = exc

    async def route_call(self, call_id, candidate_ids):
        if self.exc:
            raise self.exc
        return RoutedCall(call_id=call_id, customer_identified=True, veteran_years=3.0, unknown_candidates=("ghost",),
                          decision=RoutingDecision(agent_id="vet-1", is_blacklisted=True, fell_back=False,
                                                   reason="블랙리스트 고객 — 근속 5.0년 상담사에게 배정"))


class _Settings(RoutingSettingPort):
    async def get(self):
        return RoutingSetting(veteran_years=3.0, saved=False)

    async def save(self, veteran_years, updated_by):
        return RoutingSetting(veteran_years=veteran_years, saved=True, updated_by=updated_by)


def teardown_function():
    app.dependency_overrides.clear()


def test_DB가_없으면_배정도_설정도_501이다():
    app.dependency_overrides[require_admin] = lambda: ADMIN
    with TestClient(app) as c:
        assert c.post("/hub/routing-decisions", json={"call_id": "c1", "candidates": ["a"]}).status_code == 501
        assert c.get("/hub/routing-settings").status_code == 501


def test_배정_판정을_문자열로_돌려준다():
    app.dependency_overrides[get_agent_routing_port] = lambda: _Routing()
    with TestClient(app) as c:
        r = c.post("/hub/routing-decisions", json={"call_id": "c1", "candidates": ["vet-1", "ghost"]})
    assert r.status_code == 200
    assert r.json() == {"call_id": "c1", "assigned_agent_id": "vet-1", "is_blacklisted": "true", "fell_back": "false",
                        "reason": "블랙리스트 고객 — 근속 5.0년 상담사에게 배정", "customer_identified": "true",
                        "veteran_years": "3.0", "unknown_candidates": ["ghost"]}


def test_통화가_없으면_404다():
    app.dependency_overrides[get_agent_routing_port] = lambda: _Routing(CallNotStartedError("c1"))
    with TestClient(app) as c:
        assert c.post("/hub/routing-decisions", json={"call_id": "c1"}).status_code == 404


def test_설정은_관리자만_바꾸고_바꾼_관리자를_남긴다():
    app.dependency_overrides[get_routing_setting_port] = lambda: _Settings()
    app.dependency_overrides[require_admin] = lambda: ADMIN
    with TestClient(app) as c:
        assert c.get("/hub/routing-settings").json() == {"veteran_years": "3.0", "saved": "false", "updated_at": None, "updated_by": None}
        r = c.put("/hub/routing-settings", json={"veteran_years": 5})
        assert r.status_code == 200 and r.json()["veteran_years"] == "5.0" and r.json()["updated_by"] == "5"
        assert c.put("/hub/routing-settings", json={"veteran_years": 0}).status_code == 422
