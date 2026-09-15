# Requirement: A-6, SEC-2, QUA-1
"""HTTP 표면: **문이 잠겨 있는가**가 핵심이다.

`_project/decisions/110` 4번 — 잠기지 않은 발급 지점은 익명 업로드 프록시다. 「브라우저에 키가
없으니 안전하다」는 성립하지 않는다. 그래서 토큰 없음·틀림·미설정 셋을 전부 고정한다.
"""

import pytest
from fastapi.testclient import TestClient

from hub.app.dtos.upload_dto import DownloadTicket, StoredUpload, UploadTicket
from hub.app.ports.output.upload_storage_port import UploadStoragePort
from hub.dependencies.upload_provider import get_upload_storage_port
from main import app

_TOKEN = "test-upload-token"


class _SpyStorage(UploadStoragePort):
    async def issue_upload_ticket(self, key, content_type, max_bytes, expires_in):
        return UploadTicket(url="https://s3.example/bucket",
                            fields={"key": key, "policy": "…"}, key=key, expires_in=expires_in)

    async def list_objects(self, prefix, limit):
        from datetime import datetime, timezone
        return [StoredUpload("uploads/2026-09-14/ab-call.wav", 2048,
                             datetime(2026, 9, 14, tzinfo=timezone.utc))]

    async def issue_download_ticket(self, key, expires_in):
        return DownloadTicket(url="https://s3.example/get", key=key, expires_in=expires_in)


@pytest.fixture
def client(monkeypatch):
    # 버킷은 일부러 넣지 않는다 — 저장소는 아래에서 스텁으로 꽂는다(실제 S3 를 부르지 않는다).
    monkeypatch.setenv("UPLOAD_TOKEN", _TOKEN)
    app.dependency_overrides[get_upload_storage_port] = lambda: _SpyStorage()
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _auth(token: str = _TOKEN) -> dict:
    return {"Authorization": f"Bearer {token}"}


_BODY = {"filename": "call.wav", "content_type": "audio/wav", "content_length": 2048}


# --- 문 -----------------------------------------------------------------------------

def test_토큰이_없으면_401(client):
    assert client.post("/hub/uploads/ticket", json=_BODY).status_code == 401


def test_토큰이_틀리면_401(client):
    r = client.post("/hub/uploads/ticket", json=_BODY, headers=_auth("wrong-token"))
    assert r.status_code == 401


def test_길이가_다른_토큰도_401이다(client):
    assert client.post("/hub/uploads/ticket", json=_BODY,
                       headers=_auth(_TOKEN + "x")).status_code == 401


def test_ASCII_밖의_토큰이_와도_500이_아니라_401이다(client):
    """헤더는 latin-1 로 디코드된다 — `é`(0xE9) 같은 바이트가 실제로 들어올 수 있다.

    `secrets.compare_digest` 는 **비-ASCII `str` 에 TypeError 를 낸다.** 바이트로 비교하지
    않으면 여기서 500 이 나고, 그건 「문이 깨졌다」는 신호를 공격자에게 주는 것이다.
    """
    r = client.post("/hub/uploads/ticket", json=_BODY,
                    headers={"Authorization": "Bearer caf\xe9".encode("latin-1")})
    assert r.status_code == 401


def test_Bearer_가_아니면_401(client):
    r = client.post("/hub/uploads/ticket", json=_BODY, headers={"Authorization": _TOKEN})
    assert r.status_code == 401


def test_목록과_다시듣기도_같은_문_뒤에_있다(client):
    assert client.get("/hub/uploads").status_code == 401
    assert client.post("/hub/uploads/download-ticket",
                       json={"key": "uploads/x/y.wav"}).status_code == 401


def test_토큰이_설정되지_않으면_열리는_게_아니라_잠긴다(monkeypatch):
    """fail-closed. 설정 누락이 «아무나 통과» 가 되면 안 된다."""
    monkeypatch.delenv("UPLOAD_TOKEN", raising=False)
    app.dependency_overrides[get_upload_storage_port] = lambda: _SpyStorage()
    try:
        with TestClient(app) as c:
            assert c.post("/hub/uploads/ticket", json=_BODY, headers=_auth()).status_code == 503
    finally:
        app.dependency_overrides.clear()


# --- 정상 경로 -----------------------------------------------------------------------

def test_티켓은_url_과_폼_필드를_돌려준다(client):
    r = client.post("/hub/uploads/ticket", json=_BODY, headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["url"].startswith("https://")
    assert body["key"].startswith("uploads/")
    assert "policy" in body["fields"]
    assert body["expires_in"] == "300"   # 숫자도 문자열로 나간다(_types.StrField)


def test_음성이_아니면_400(client):
    r = client.post("/hub/uploads/ticket",
                    json={**_BODY, "content_type": "application/pdf"}, headers=_auth())
    assert r.status_code == 400


def test_보관_프리픽스_밖의_키는_400(client):
    r = client.post("/hub/uploads/download-ticket",
                    json={"key": "datasets/aihub/원본.wav"}, headers=_auth())
    assert r.status_code == 400


def test_목록은_크기를_문자열로_돌려준다(client):
    r = client.get("/hub/uploads", headers=_auth())
    assert r.status_code == 200
    assert r.json()["total"] == "1" and r.json()["items"][0]["size"] == "2048"


# --- 페이지 -------------------------------------------------------------------------

def test_페이지는_토큰_없이_열리고_비밀이_없다(client):
    r = client.get("/hub/uploads/page")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert _TOKEN not in r.text          # 토큰이 페이지에 박히지 않는다
    assert "AWS_SECRET" not in r.text and "aws_access_key" not in r.text.lower()
