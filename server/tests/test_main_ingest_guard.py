# Requirement: SEC-2, A-3, QUA-1
"""쓰기 경로의 문 — 콜 미디에이터만 서버에 쓸 수 있는가 (`_project/decisions/120`).

2026-09-20 운영 왕복에서 `POST /hub/calls`·`/hub/transcripts` 등이 **토큰 없이 200** 이었다.
문 자체는 `hub/dependencies/ingest_guard.py`, 어디에 거는지는 합성 루트(`main.py`)다 — 그래서 테스트도 여기 둔다.
"""

import pytest
from fastapi.testclient import TestClient

from main import app

TOKEN = "svc-token-for-test-0123456789"

# 콜 미디에이터 전용 쓰기 경로 — 본문은 일부러 비운다. **문이 먼저 서는지**만 본다
# (문을 지나면 422/501 이 나온다. 401 이 아니면 지나간 것이다).
INGEST_PATHS = [
    "/hub/calls", "/hub/transcripts", "/hub/recommendations", "/hub/call-guard-checks",
    "/hub/compliance-checks", "/hub/required-docs-checks", "/hub/closure-checks",
    "/hub/routing-decisions",  # decisions/126 — 콜 미디에이터가 통화 시작 직후 부른다
]


def _env(monkeypatch, token):
    for key in ("DATABASE_URL", "ELASTICSEARCH_URL"):
        monkeypatch.delenv(key, raising=False)
    if token is None:
        monkeypatch.delenv("INGEST_SERVICE_TOKEN", raising=False)
    else:
        monkeypatch.setenv("INGEST_SERVICE_TOKEN", token)


@pytest.mark.parametrize("path", INGEST_PATHS)
def test_토큰이_설정되면_없는_요청은_401_이다(monkeypatch, path):
    _env(monkeypatch, TOKEN)
    with TestClient(app) as client:
        assert client.post(path, json={}).status_code == 401


@pytest.mark.parametrize("path", INGEST_PATHS)
def test_맞는_토큰이면_문을_지난다(monkeypatch, path):
    _env(monkeypatch, TOKEN)
    with TestClient(app) as client:
        res = client.post(path, json={}, headers={"Authorization": f"Bearer {TOKEN}"})
    assert res.status_code != 401          # 빈 본문이라 422/501 이다 — 문은 지났다


@pytest.mark.parametrize("header", ["Bearer wrong-token", "Basic " + TOKEN, TOKEN, "Bearer ", "bearer"])
def test_틀린_토큰·다른_스킴은_401_이다(monkeypatch, header):
    _env(monkeypatch, TOKEN)
    with TestClient(app) as client:
        assert client.post("/hub/transcripts", json={}, headers={"Authorization": header}).status_code == 401


def test_비ASCII_토큰은_500_이_아니라_401_이다(monkeypatch):
    """`compare_digest` 는 비-ASCII **문자열**에 TypeError 를 낸다 — 업로드 문이 같은 함정을 겪었다.

    헤더는 latin-1 로 디코드된다 — `é`(0xE9) 같은 바이트가 실제로 들어올 수 있다(`test_upload_router` 와 같은 방식).
    """
    _env(monkeypatch, TOKEN)
    with TestClient(app) as client:
        res = client.post("/hub/transcripts", json={},
                          headers={"Authorization": "Bearer café".encode("latin-1")})
    assert res.status_code == 401


@pytest.mark.parametrize("path", INGEST_PATHS)
def test_미설정이면_닫는다(monkeypatch, path):
    """시크릿을 되돌리거나 키를 빠뜨려도 **문이 조용히 열리지 않는다** — 업로드 문(`110`)·`/close`(`315`)와 같다.

    2026-09-22 까지는 「없으면 연다」였다(120 「전환 순서」 1~3번의 이행기). 미디에이터가 토큰을 보내기 시작해 4번으로 닫았다.
    """
    _env(monkeypatch, None)
    with TestClient(app) as client:
        assert client.post(path, json={}).status_code == 401
        assert client.post(path, json={}, headers={"Authorization": "Bearer anything"}).status_code == 401


def test_잠금_상태를_health_가_말한다(monkeypatch):
    """미설정은 「열림」이 아니라 「쓰기 전부 401」이다 — `unset` 이 그것을 말한다. 조용하면 안 된다."""
    _env(monkeypatch, None)
    with TestClient(app) as client:
        assert client.get("/health").json()["ingest_guard"] == "unset"
    _env(monkeypatch, TOKEN)
    with TestClient(app) as client:
        body = client.get("/health").json()
    assert body["ingest_guard"] == "locked"
    assert TOKEN not in str(body)          # 상태만 싣는다 — 값은 싣지 않는다(SEC-2)


@pytest.mark.parametrize("path", ["/health", "/hub/calls", "/hub/knowledge-gaps"])
def test_읽기_경로는_잠기지_않는다(monkeypatch, path):
    """대시보드가 직접 부르는 GET 은 이 문 밖이다 — `GET /hub/calls`(목록)는 `POST /hub/calls`(통화 시작)와 라우터가 다르다."""
    _env(monkeypatch, TOKEN)
    with TestClient(app) as client:
        assert client.get(path).status_code != 401
