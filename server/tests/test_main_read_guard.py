# Requirement: SEC-1, SEC-2, QUA-1
"""읽기 경로의 문 — 통화 목록·전사·통화 기록·수동 검색(`_project/decisions/322`).

운영에서 `GET /hub/calls` 가 토큰 없이 실제 음성 테스트 통화까지 보여 줬다. 부르는 쪽은 상담원 화면(`apps/call`)과
합성 통화 검사(`scripts/persona_sim/e2e_check.py`) — **둘 다 아직 토큰을 싣지 않는다.** 그래서 `120` 처럼 두 단계로 닫는다:
① 서버가 상담원 토큰·서비스 토큰을 **받는다**(틀린 토큰은 지금도 401) ② `READ_AUTH_REQUIRED=true` 로 토큰 없는 요청을 막는다.
"""

import pytest
from fastapi.testclient import TestClient

from hub.dependencies.read_guard import get_agent_token_checker
from main import app

SERVICE = "svc-token-for-test-0123456789"
AGENT = "cga_good-agent-token"

READ_PATHS = [
    ("get", "/hub/calls", None),
    ("get", "/hub/calls/c_001/transcript", None),
    ("get", "/hub/calls/c_001/record", None),
    ("post", "/hub/search", {"utterance": "여권 재발급"}),
]


async def _agent_ok(token: str) -> bool:
    return token == AGENT


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for key in ("DATABASE_URL", "ELASTICSEARCH_URL", "READ_AUTH_REQUIRED"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("INGEST_SERVICE_TOKEN", SERVICE)
    app.dependency_overrides[get_agent_token_checker] = lambda: _agent_ok
    yield
    app.dependency_overrides.clear()


def _call(client, method, path, body, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    return client.post(path, json=body, headers=headers) if method == "post" else client.get(path, headers=headers)


@pytest.mark.parametrize("method, path, body", READ_PATHS)
def test_이행기에는_토큰_없는_읽기가_지나간다(method, path, body):
    """상담원 화면이 토큰을 싣기 전에 막으면 운영 화면이 깨진다 — `READ_AUTH_REQUIRED` 가 없으면 지나간다(DB 없음 501 등)."""
    with TestClient(app) as c:
        assert _call(c, method, path, body).status_code != 401


@pytest.mark.parametrize("method, path, body", READ_PATHS)
def test_켜면_토큰_없는_읽기는_401이다(monkeypatch, method, path, body):
    monkeypatch.setenv("READ_AUTH_REQUIRED", "true")
    with TestClient(app) as c:
        assert _call(c, method, path, body).status_code == 401


@pytest.mark.parametrize("token", [AGENT, SERVICE])
@pytest.mark.parametrize("method, path, body", READ_PATHS)
def test_켜도_상담원_토큰이나_서비스_토큰이면_지나간다(monkeypatch, method, path, body, token):
    monkeypatch.setenv("READ_AUTH_REQUIRED", "true")
    with TestClient(app) as c:
        assert _call(c, method, path, body, token).status_code != 401


@pytest.mark.parametrize("method, path, body", READ_PATHS)
def test_이행기에도_틀린_토큰은_401이다(method, path, body):
    """토큰을 실었는데 틀리면 조용히 넘기지 않는다 — 프론트가 잘못된 값을 싣고 있는 것을 이행기에 찾는다."""
    with TestClient(app) as c:
        assert _call(c, method, path, body, "cga_wrong").status_code == 401


def test_잠금_상태를_health_가_말한다(monkeypatch):
    with TestClient(app) as c:
        assert c.get("/health").json()["read_guard"] == "open"
    monkeypatch.setenv("READ_AUTH_REQUIRED", "true")
    with TestClient(app) as c:
        assert c.get("/health").json()["read_guard"] == "locked"
