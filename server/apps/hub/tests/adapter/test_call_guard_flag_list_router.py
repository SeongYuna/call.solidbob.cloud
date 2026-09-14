# Requirement: C-6, QUA-1
"""HTTP 표면: 로그인 없으면 401 · 값은 문자열."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.ports.input.current_admin_use_case import CurrentAdminUseCase
from admin_auth.dependencies.use_case_providers import get_current_admin_use_case
from hub.app.dtos.call_guard_flag_list_dto import CallGuardFlagRecord
from hub.app.ports.output.call_guard_flag_query_port import CallGuardFlagQueryPort
from hub.dependencies.call_guard_flag_list_provider import get_call_guard_flag_query_port
from main import app


class _Port(CallGuardFlagQueryPort):
    async def list_flags(self, call_id, category, limit, offset):
        return [CallGuardFlagRecord(id=9, call_id="c1", segment_id=2, category="insult", phrase="병신", span=(3, 5),
                                    source_doc_id="DASAN-MANUAL-5.1", detected_at=datetime(2026, 9, 14, tzinfo=timezone.utc))]

    async def count_flags(self, call_id, category):
        return 1


class _NoSession(CurrentAdminUseCase):
    async def current(self, access_token):
        return None


def test_로그인_없으면_401_로그인하면_문자열_값으로_준다():
    app.dependency_overrides[get_call_guard_flag_query_port] = lambda: _Port()
    app.dependency_overrides[get_current_admin_use_case] = lambda: _NoSession()
    try:
        with TestClient(app) as client:
            assert client.get("/hub/call-guard-flags", headers={"authorization": "Bearer x"}).status_code == 401
            app.dependency_overrides[require_admin] = lambda: AdminAccount(id=1, email="a@example.com", name=None)
            r = client.get("/hub/call-guard-flags?category=insult")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json() == {
        "flags": [{"id": "9", "call_id": "c1", "segment_id": "2", "category": "insult", "phrase": "병신",
                   "span": ["3", "5"], "source_doc_id": "DASAN-MANUAL-5.1", "detected_at": "2026-09-14T00:00:00+00:00"}],
        "total": "1", "limit": "100", "offset": "0",
    }
