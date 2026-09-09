# Requirement: [Task 1], QUA-1
"""브라우저(apps/dashboard)가 다른 origin 에서 코어 API 를 부를 수 있는지 — CORS.

프론트가 붙는 운영 주소는 `server.solidbob.cloud` 하나지만(런북 16-2·18), 대시보드를 어디서
서빙할지는 아직 정해지지 않았고 로컬 개발은 Vite(5173) → uvicorn(8000) 으로 origin 이 항상 다르다.
허용 origin 은 `CORS_ALLOWED_ORIGINS` 로 받고, 기본값은 로컬 Vite 뿐이다 — 운영 주소를 기본값으로 굳히지 않는다.
"""

from fastapi.testclient import TestClient

from core.config import load_settings
from main import app

VITE_DEV_ORIGIN = "http://localhost:5173"


def test_로컬_Vite_origin_은_기본으로_허용된다(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    with TestClient(app) as client:
        res = client.options(
            "/hub/closure-checks",
            headers={
                "Origin": VITE_DEV_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    assert res.status_code == 200, res.text
    assert res.headers.get("access-control-allow-origin") == VITE_DEV_ORIGIN


def test_목록에_없는_origin_에는_허용_헤더를_주지_않는다():
    with TestClient(app) as client:
        res = client.get("/health", headers={"Origin": "https://evil.example"})
    assert res.status_code == 200
    assert "access-control-allow-origin" not in res.headers


def test_CORS_ALLOWED_ORIGINS_는_쉼표로_나누고_공백을_버린다(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", " https://app.example , http://localhost:5173 ")
    assert load_settings().cors_allowed_origins == ("https://app.example", "http://localhost:5173")


def test_CORS_ALLOWED_ORIGINS_가_비어_있으면_로컬_Vite_기본값(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    assert load_settings().cors_allowed_origins == (VITE_DEV_ORIGIN, "http://127.0.0.1:5173")
