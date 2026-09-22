# Requirement: SEC-2, QUA-1
"""`/health` 의 배포 버전 — 밖에서 어느 이미지 태그가 떠 있는지 알 길이 없었다(09-22 하루에 태그가 네 번 겹쳤다, `w6-server-loose-ends` ①).

값은 빌드 인자 `APP_VERSION` 이 이미지에 굽힌다(`infra/docker/server.Dockerfile` · `release.yml`). 비밀이 아니다.
"""

from fastapi.testclient import TestClient

from main import app


def test_이미지에_구운_태그를_싣는다(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "0.1.35")
    with TestClient(app) as c:
        assert c.get("/health").json()["version"] == "0.1.35"


def test_태그가_없으면_unknown_이다(monkeypatch):
    """로컬 `uvicorn` 은 이미지가 아니다 — 지어낸 버전을 싣지 않는다."""
    monkeypatch.delenv("APP_VERSION", raising=False)
    with TestClient(app) as c:
        assert c.get("/health").json()["version"] == "unknown"
