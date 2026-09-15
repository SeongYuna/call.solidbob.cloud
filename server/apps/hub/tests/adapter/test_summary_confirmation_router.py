# Requirement: D-1, D-2, D-3, QUA-1
"""HTTP 표면: 상담원 토큰 필수 · DB 없으면 501 · 없는 통화 404 · 이미 확정 409 · 값은 문자열."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from agent_auth.dependencies.providers import get_agent_token_port
from agent_auth.tests._fakes import FakeAgentTokens
from hub.app.ports.output.postcall_record_port import SummaryAlreadyConfirmedError
from hub.app.ports.output.summary_confirmation_port import SummaryConfirmationPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.summary_confirmation_provider import get_summary_confirmation_port
from main import app

TOKEN = "cga_summary-confirm-test"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
BODY = {"summary_text": "전입신고 서류 문의", "inquiry_type": "전입신고", "follow_up_actions": ["목록 문자 발송"]}


class _Port(SummaryConfirmationPort):
    def __init__(self, exc=None):
        self.exc = exc

    async def confirm(self, call_id, *, summary_text, inquiry_type, follow_up_actions):
        if self.exc is not None:
            raise self.exc
        return datetime(2026, 9, 15, 4, 0, tzinfo=timezone.utc)


def _post(port=None, headers=AUTH, body=BODY):
    tokens = FakeAgentTokens()
    tokens.seed("agent-7", TOKEN)
    app.dependency_overrides[get_agent_token_port] = lambda: tokens
    if port is not None:
        app.dependency_overrides[get_summary_confirmation_port] = lambda: port
    try:
        with TestClient(app) as client:
            return client.post("/hub/calls/c1/summary-confirmation", json=body, headers=headers)
    finally:
        app.dependency_overrides.clear()


def test_토큰이_없거나_틀리면_401이다():
    assert _post(_Port(), headers={}).status_code == 401
    assert _post(_Port(), headers={"Authorization": "Bearer cga_wrong"}).status_code == 401


def test_PostgreSQL_미설정이면_501이다():
    assert _post().status_code == 501


def test_확정본을_문자열로_돌려준다():
    r = _post(_Port())
    assert r.status_code == 200
    assert r.json() == {"call_id": "c1", "summary_text": "전입신고 서류 문의", "inquiry_type": "전입신고",
                        "follow_up_actions": ["목록 문자 발송"], "confirmed": "true",
                        "confirmed_at": "2026-09-15T04:00:00+00:00"}


def test_없는_통화_404_이미_확정_409_빈_요약_422():
    assert _post(_Port(CallNotStartedError("c1"))).status_code == 404
    assert _post(_Port(SummaryAlreadyConfirmedError("c1"))).status_code == 409
    assert _post(_Port(), body={**BODY, "summary_text": ""}).status_code == 422
