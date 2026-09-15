# Requirement: D-1, D-2, D-3, QUA-1
"""HTTP 표면: 상담원 토큰 필수 · 확정 전 409 · 없는 통화 404 · 이력 조회 · DB 없음 501."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from agent_auth.dependencies.providers import get_agent_token_port
from agent_auth.tests._fakes import FakeAgentTokens
from hub.app.dtos.summary_revision_dto import SummaryRevision
from hub.app.ports.output.summary_revision_port import SummaryNotConfirmedError, SummaryRevisionPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.summary_revision_provider import get_summary_revision_port
from main import app

TOKEN = "cga_summary-revision-test"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
BODY = {"summary_text": "고친 요약", "reason": "유형 오기", "inquiry_type": "전입신고", "follow_up_actions": ["회신"]}
REV = SummaryRevision(revision_id=4, call_id="c1", previous_summary_text="처음 확정", previous_inquiry_type="기타",
                      reason="유형 오기", revised_at=datetime(2026, 9, 15, 5, 0, tzinfo=timezone.utc))


class _Port(SummaryRevisionPort):
    def __init__(self, exc=None):
        self.exc = exc

    async def revise(self, call_id, **kw):
        if self.exc:
            raise self.exc
        return REV

    async def list_revisions(self, call_id):
        if self.exc:
            raise self.exc
        return [REV]


def _client(port=None):
    tokens = FakeAgentTokens()
    tokens.seed("agent-7", TOKEN)
    app.dependency_overrides[get_agent_token_port] = lambda: tokens
    if port is not None:
        app.dependency_overrides[get_summary_revision_port] = lambda: port
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_토큰_없으면_401_DB_없으면_501():
    with _client() as c:
        assert c.post("/hub/calls/c1/summary-revision", json=BODY).status_code == 401
        assert c.get("/hub/calls/c1/summary-revisions").status_code == 401
        assert c.post("/hub/calls/c1/summary-revision", json=BODY, headers=AUTH).status_code == 501


def test_고치고_이전_값을_이력으로_돌려준다():
    with _client(_Port()) as c:
        r = c.post("/hub/calls/c1/summary-revision", json=BODY, headers=AUTH)
        listed = c.get("/hub/calls/c1/summary-revisions", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["revision"] == {"revision_id": "4", "call_id": "c1", "previous_summary_text": "처음 확정",
                                    "previous_inquiry_type": "기타", "reason": "유형 오기",
                                    "revised_at": "2026-09-15T05:00:00+00:00"}
    assert listed.json()["revisions"][0]["revision_id"] == "4"


def test_확정_전_409_없는_통화_404_사유_없음_422():
    with _client(_Port(SummaryNotConfirmedError("c1"))) as c:
        assert c.post("/hub/calls/c1/summary-revision", json=BODY, headers=AUTH).status_code == 409
    with _client(_Port(CallNotStartedError("c1"))) as c:
        assert c.post("/hub/calls/c1/summary-revision", json=BODY, headers=AUTH).status_code == 404
        assert c.get("/hub/calls/c1/summary-revisions", headers=AUTH).status_code == 404
    with _client(_Port()) as c:
        assert c.post("/hub/calls/c1/summary-revision", json={**BODY, "reason": ""}, headers=AUTH).status_code == 422
