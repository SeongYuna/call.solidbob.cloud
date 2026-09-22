# Requirement: J-3, QUA-1
"""GET /hub/admin-stats — 로그인 없으면 401 · DB 없으면 501(0 을 지어내지 않는다) · 전부 문자열."""

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from hub.app.dtos.admin_stats_dto import AdminStats
from hub.app.ports.output.admin_stats_port import AdminStatsPort
from hub.dependencies.admin_stats_provider import get_admin_stats_port
from main import app


class _Port(AdminStatsPort):
    async def count(self):
        return AdminStats(5, 3, 2, 1, 1, 0, 0, 0, counted_at=datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc),
                          calls_today=2, call_guard_flags_today=1, requests_today=1, today=date(2026, 9, 22))


def test_로그인_없이는_401이다(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as c:
        assert c.get("/hub/admin-stats").status_code == 401


def test_DB가_없으면_0이_아니라_501이다(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app.dependency_overrides[require_admin] = lambda: AdminAccount(id=1, email="a@x", name=None)
    try:
        with TestClient(app) as c:
            assert c.get("/hub/admin-stats").status_code == 501
    finally:
        app.dependency_overrides.clear()


def test_건수를_문자열로_돌려준다():
    app.dependency_overrides[require_admin] = lambda: AdminAccount(id=1, email="a@x", name=None)
    app.dependency_overrides[get_admin_stats_port] = lambda: _Port()
    try:
        with TestClient(app) as c:
            r = c.get("/hub/admin-stats")
        assert r.status_code == 200
        assert r.json() == {
            "calls_total": "5", "calls_closed": "3", "call_guard_flags": "2", "pending_requests": "1",
            "active_entries": "1", "routing_decisions": "0", "routing_blacklisted": "0", "routing_fell_back": "0",
            "counted_at": "2026-09-22T01:00:00+00:00",
            # 오늘(KST) 칸 — w6-admin-stats-today. 누적 칸과 따로 센다
            "calls_today": "2", "call_guard_flags_today": "1", "requests_today": "1", "today": "2026-09-22",
        }
    finally:
        app.dependency_overrides.clear()
