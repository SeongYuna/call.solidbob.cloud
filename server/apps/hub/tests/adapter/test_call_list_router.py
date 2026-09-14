# Requirement: D-1, D-2, QUA-1
"""HTTP 표면: PostgreSQL 미설정이면 501, 설정되면 값은 전부 문자열."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from hub.app.dtos.call_list_dto import CallListItem
from hub.app.ports.output.call_list_port import CallListPort
from hub.dependencies.call_list_provider import get_call_list_port
from main import app


class _Port(CallListPort):
    async def list_calls(self, limit, offset, customer_id):
        return [CallListItem(
            call_id="test-1", domain="dasan", started_at=datetime(2026, 9, 14, 1, 2, 3, tzinfo=timezone.utc),
            ended_at=None, status="in_progress", stt_engine="google-stt+diarize", channel_count=1,
            customer_id=None, inquiry_type=None, summary_confirmed=False,
        )]

    async def count_calls(self, customer_id):
        return 1


def test_PostgreSQL_미설정이면_501이다():
    with TestClient(app) as client:
        assert client.get("/hub/calls").status_code == 501


def test_목록을_문자열_값으로_돌려준다():
    app.dependency_overrides[get_call_list_port] = lambda: _Port()
    try:
        with TestClient(app) as client:
            r = client.get("/hub/calls?limit=5")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json() == {
        "calls": [{
            "call_id": "test-1", "domain": "dasan", "started_at": "2026-09-14T01:02:03+00:00", "ended_at": None,
            "status": "in_progress", "stt_engine": "google-stt+diarize", "channel_count": "1", "customer_id": None,
            "inquiry_type": None, "summary_confirmed": "false",
        }],
        "total": "1", "limit": "5", "offset": "0",
    }


def test_통화_시작_POST_와_경로가_겹쳐도_따로_돈다():
    """같은 `/hub/calls` 에 POST(통화 시작)와 GET(목록)이 있다 — 메서드로 갈린다."""
    app.dependency_overrides[get_call_list_port] = lambda: _Port()
    try:
        with TestClient(app) as client:
            assert client.get("/hub/calls").status_code == 200
            assert client.post("/hub/calls", json={}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_고객_필터는_64자_HMAC_식별자를_받는다():
    """E2E 에서 잡혔다 — 필터 길이가 옛 컬럼 길이(40)라 실제 식별자가 422 였다 (decisions/304)."""
    app.dependency_overrides[get_call_list_port] = lambda: _Port()
    try:
        with TestClient(app) as client:
            assert client.get("/hub/calls?customer_id=" + "a" * 64).status_code == 200
            assert client.get("/hub/calls?customer_id=" + "a" * 65).status_code == 422
    finally:
        app.dependency_overrides.clear()
