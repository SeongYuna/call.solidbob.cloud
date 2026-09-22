# Requirement: SEC-1, D-1, E-1, QUA-1
"""열려 있던 쓰기 둘에 단 문(`_project/decisions/315`).

- `POST /hub/calls/{id}/close` — 상담원 토큰 **또는** 서비스 토큰(`INGEST_SERVICE_TOKEN`). 서비스 토큰이 미설정이어도 열지 않는다
- `POST /hub/cards/{id}/feedback` — 상담원 토큰을 확인하되 **누구인지는 버린다**(부록 A-1)
"""

import dataclasses
import inspect

import pytest
from fastapi.testclient import TestClient

from agent_auth.app.ports.input.current_agent_use_case import CurrentAgentUseCase
from agent_auth.dependencies.use_case_providers import get_current_agent_use_case
from hub.adapter.inbound.api.v1.card_feedback_router import record_card_feedback
from hub.app.dtos.card_feedback_dto import CardFeedback
from hub.app.ports.output import CardFeedbackPort
from hub.dependencies.card_feedback_provider import get_card_feedback_port
from main import app

SERVICE = "svc-token-for-test-0123456789"
AGENT = "cga_good-agent-token"
CLOSE = ("/hub/calls/c_001/close", {"call_id": "c_001", "segments": [
    {"segment_id": 1, "speaker": "customer", "text": "여권 재발급 서류가 뭐예요", "is_final": True}]})
FEEDBACK = ("/hub/cards/42/feedback", {"action": "adopted"})


class _Agents(CurrentAgentUseCase):
    async def current(self, token):
        return "a_01" if token == AGENT else None


class _Feedback(CardFeedbackPort):
    def __init__(self):
        self.seen = []

    async def append(self, feedback):
        self.seen.append(feedback)
        return 7


@pytest.fixture
def feedback():
    return _Feedback()


@pytest.fixture
def client(monkeypatch, feedback):
    for key in ("DATABASE_URL", "ELASTICSEARCH_URL", "INGEST_SERVICE_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    app.dependency_overrides[get_current_agent_use_case] = lambda: _Agents()
    app.dependency_overrides[get_card_feedback_port] = lambda: feedback
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _post(client, route, header=None):
    path, body = route
    return client.post(path, json=body, headers={"Authorization": header} if header else {})


@pytest.mark.parametrize("route", [CLOSE, FEEDBACK], ids=["close", "feedback"])
@pytest.mark.parametrize("header", [None, "Bearer cga_wrong", "Basic " + AGENT, "Bearer "])
def test_토큰이_없거나_틀리면_401이다(client, route, header):
    assert _post(client, route, header).status_code == 401


@pytest.mark.parametrize("route,ok", [(CLOSE, 200), (FEEDBACK, 201)], ids=["close", "feedback"])
def test_맞는_상담원_토큰이면_통과한다(client, route, ok):
    assert _post(client, route, f"Bearer {AGENT}").status_code == ok


def test_close_는_서비스_토큰으로도_통과한다(monkeypatch):
    """합성 통화 재생기(`replay_persona_call.ts --close`)가 쓰는 길 — 사람이 없다."""
    monkeypatch.setenv("INGEST_SERVICE_TOKEN", SERVICE)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app.dependency_overrides[get_current_agent_use_case] = lambda: _Agents()
    try:
        with TestClient(app) as c:
            assert _post(c, CLOSE, f"Bearer {SERVICE}").status_code == 200
            assert _post(c, CLOSE, "Bearer svc-wrong").status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_서비스_토큰은_카드_피드백을_열지_않는다(monkeypatch, feedback):
    """카드 피드백은 상담원 화면만 부른다 — 서비스 토큰은 여기 쓸 일이 없다."""
    monkeypatch.setenv("INGEST_SERVICE_TOKEN", SERVICE)
    app.dependency_overrides[get_current_agent_use_case] = lambda: _Agents()
    app.dependency_overrides[get_card_feedback_port] = lambda: feedback
    try:
        with TestClient(app) as c:
            assert _post(c, FEEDBACK, f"Bearer {SERVICE}").status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_카드_피드백은_상담원을_확인만_하고_저장소로_넘기지_않는다(client, feedback):
    """부록 A-1 — 받지 않으면 집계할 수도 없다. 라우트 함수 인자와 DTO 둘 다에 상담원 자리가 없다."""
    assert _post(client, FEEDBACK, f"Bearer {AGENT}").status_code == 201
    (saved,) = feedback.seen
    assert {f.name for f in dataclasses.fields(saved)} == {"card_id", "action"}
    assert {f.name for f in dataclasses.fields(CardFeedback)} == {"card_id", "action"}
    assert not any("agent" in name for name in inspect.signature(record_card_feedback).parameters)
