# Requirement: 관리자 로그인(구글), QUA-1
"""헤더가 없으면 인프라(Redis·DB)를 타기 전에 401 — 운영 `0.1.8` 에서 500 으로 재현된 것을 고정한다.

이 테스트는 의존성을 **덮지 않는다.** 테스트 환경에는 REDIS_URL 이 없어서, 가드가 헤더보다 Redis 프로바이더를
먼저 풀면 `RuntimeError` 로 터진다 — 운영에서 겪은 그대로다.
"""

import pytest
from fastapi.testclient import TestClient

from main import app

ADMIN_PATHS = [
    ("get", "/admin/auth/me"),
    ("get", "/admin/agent-tokens"),
    ("post", "/admin/agent-tokens/1/revoke"),
    ("get", "/hub/blacklist-requests"),
    ("get", "/hub/blacklist-entries"),
    ("get", "/hub/call-guard-flags"),
    ("post", "/hub/blacklist-entries/1/expiry"),
    ("get", "/hub/blacklist-entries/1/expiry-changes"),
    ("post", "/hub/blacklist-retention/purge"),
    ("get", "/hub/routing-settings"),
    ("put", "/hub/routing-settings"),
]


@pytest.fixture
def client(monkeypatch):
    for key in ("REDIS_URL", "ADMIN_JWT_SECRET"):
        monkeypatch.delenv(key, raising=False)
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.mark.parametrize("method,path", ADMIN_PATHS)
def test_헤더가_없으면_Redis가_없어도_401이다(client, method, path):
    assert getattr(client, method)(path).status_code == 401


@pytest.mark.parametrize("method,path", ADMIN_PATHS)
def test_Bearer가_아닌_헤더도_401이다(client, method, path):
    assert getattr(client, method)(path, headers={"Authorization": "Basic abc"}).status_code == 401


def test_상담원_토큰_경로도_헤더가_없으면_401이다(client):
    """상담원 가드도 저장소(DB 없음 501)보다 헤더를 먼저 본다."""
    assert client.post("/hub/calls/c1/summary-confirmation", json={"summary_text": "x"}).status_code == 401
    assert client.post("/hub/blacklist-requests", json={"call_id": "c1", "reason": "x"}).status_code == 401

