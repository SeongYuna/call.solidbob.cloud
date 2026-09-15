# Requirement: J-4, 관리자 로그인(구글), QUA-1
"""HTTP 표면: 관리자 4개 경로 — 로그인 없으면 401, 결정자 agent_id 없으면 409, 상태 충돌 409."""

import pytest
from fastapi.testclient import TestClient

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.ports.input.current_admin_use_case import CurrentAdminUseCase
from admin_auth.dependencies.use_case_providers import get_current_admin_use_case
from hub.app.ports.output.blacklist_port import BlacklistConflict, BlacklistNotFound, ExpiryBeyondCap
from hub.dependencies.blacklist_provider import get_blacklist_port
from hub.tests.app.use_cases._blacklist_stubs import StubBlacklist
from main import app

ADMIN = AdminAccount(id=1, email="admin@example.com", name=None, agent_id="admin-1")


class _NoSession(CurrentAdminUseCase):
    """세션이 없는 관리자 — 실제 가드(`require_admin`)가 401 을 내는지 본다. Redis 없이 돈다."""

    async def current(self, access_token):
        return None


@pytest.fixture
def client():
    app.dependency_overrides[get_blacklist_port] = lambda: StubBlacklist()
    app.dependency_overrides[get_current_admin_use_case] = lambda: _NoSession()
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("method,path,body", [
    ("get", "/hub/blacklist-requests", None),
    ("post", "/hub/blacklist-requests/7/decision", {"approve": False}),
    ("get", "/hub/blacklist-entries", None),
    ("post", "/hub/blacklist-entries/3/release", {"reason": "오인"}),
    ("post", "/hub/blacklist-entries/3/expiry", {"expires_in_days": 30, "reason": "연장"}),
    ("get", "/hub/blacklist-entries/3/expiry-changes", None),
])
def test_로그인_없이는_401이다(client, method, path, body):
    kwargs = {"json": body} if body is not None else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401
    assert getattr(client, method)(path, headers={"authorization": "Bearer expired-token"}, **kwargs).status_code == 401


def test_승인하면_결정자는_로그인한_관리자의_agent_id_다(client):
    app.dependency_overrides[require_admin] = lambda: ADMIN
    r = client.post("/hub/blacklist-requests/7/decision", json={"approve": True, "expires_in_days": 30})
    assert r.status_code == 200 and r.json()["request"]["status"] == "approved"


def test_관리자에_agent_id_가_없으면_409이다(client):
    app.dependency_overrides[require_admin] = lambda: AdminAccount(id=2, email="b@example.com", name=None)
    r = client.post("/hub/blacklist-entries/3/release", json={"reason": "오인"})
    assert r.status_code == 409


def test_승인에_만료_일수가_없으면_422_상태_충돌은_409(client):
    app.dependency_overrides[require_admin] = lambda: ADMIN
    assert client.post("/hub/blacklist-requests/7/decision", json={"approve": True}).status_code == 422

    class _Decided(StubBlacklist):
        async def decide(self, *a, **kw):
            raise BlacklistConflict("이미 결정된 요청")

    app.dependency_overrides[get_blacklist_port] = lambda: _Decided()
    assert client.post("/hub/blacklist-requests/7/decision", json={"approve": False}).status_code == 409


def test_목록은_상태_필터와_적용_중_필터를_받는다(client):
    app.dependency_overrides[require_admin] = lambda: ADMIN
    assert client.get("/hub/blacklist-requests?status=pending").json() == {"requests": []}
    assert client.get("/hub/blacklist-requests?status=released").status_code == 422
    assert client.get("/hub/blacklist-entries?active_only=true").json() == {"entries": []}
    r = client.post("/hub/blacklist-entries/3/release", json={"reason": "오인 신고"})
    assert r.status_code == 200 and r.json()["entry"]["released_by"] == "admin-1"


def test_만료_변경은_로그인한_관리자의_agent_id로_기록된다(client):
    app.dependency_overrides[require_admin] = lambda: ADMIN
    r = client.post("/hub/blacklist-entries/3/expiry", json={"expires_in_days": 90, "reason": "재발 우려"})
    assert r.status_code == 200
    b = r.json()
    assert b["change"]["changed_by"] == "admin-1" and b["change"]["entry_id"] == "3"
    assert b["entry"]["expires_at"] == b["change"]["new_expires_at"]
    assert client.get("/hub/blacklist-entries/3/expiry-changes").json() == {"changes": []}


def test_만료_변경_검증_422_해제된_등록_409_없는_등록_404(client):
    app.dependency_overrides[require_admin] = lambda: ADMIN
    assert client.post("/hub/blacklist-entries/3/expiry", json={"expires_in_days": 366, "reason": "x"}).status_code == 422
    assert client.post("/hub/blacklist-entries/3/expiry", json={"expires_in_days": 30}).status_code == 422  # 사유 필수

    class _Released(StubBlacklist):
        async def change_expiry(self, *a, **kw):
            raise BlacklistConflict("이미 해제된 등록입니다")

    class _Missing(StubBlacklist):
        async def change_expiry(self, *a, **kw):
            raise BlacklistNotFound("등록이 없습니다")

        async def list_expiry_changes(self, entry_id):
            raise BlacklistNotFound("등록이 없습니다")

    app.dependency_overrides[get_blacklist_port] = lambda: _Released()
    assert client.post("/hub/blacklist-entries/3/expiry", json={"expires_in_days": 30, "reason": "x"}).status_code == 409
    app.dependency_overrides[get_blacklist_port] = lambda: _Missing()
    assert client.post("/hub/blacklist-entries/3/expiry", json={"expires_in_days": 30, "reason": "x"}).status_code == 404
    assert client.get("/hub/blacklist-entries/3/expiry-changes").status_code == 404


def test_누적_상한을_넘는_연장은_422다(client):
    """상태 충돌(409)이 아니라 입력이 정책을 넘은 것이다 — 응답에 언제까지 가능한지가 실린다."""
    from datetime import datetime, timezone

    app.dependency_overrides[require_admin] = lambda: ADMIN

    class _Capped(StubBlacklist):
        async def change_expiry(self, *a, **kw):
            raise ExpiryBeyondCap(datetime(2027, 9, 15, tzinfo=timezone.utc))

    app.dependency_overrides[get_blacklist_port] = lambda: _Capped()
    r = client.post("/hub/blacklist-entries/3/expiry", json={"expires_in_days": 300, "reason": "연장"})
    assert r.status_code == 422 and "2027-09-15" in r.json()["detail"]


def test_보존_기간_정리는_비운_건수를_문자열로_돌려준다(client):
    app.dependency_overrides[require_admin] = lambda: ADMIN
    r = client.post("/hub/blacklist-retention/purge")
    assert r.status_code == 200
    assert r.json() == {"retention_days": "180", "cutoff": "2026-09-14T03:00:00+00:00",
                        "expiry_change_reasons_purged": "2", "rejected_requests_purged": "1"}

