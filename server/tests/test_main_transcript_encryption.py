# Requirement: C-5, SEC-1, SEC-2, QUA-1
"""전사 본문 암호화(`decisions/326`)의 합성 루트 — `/health` 가 켜졌는지 말하고, 잘못된 키로는 뜨지 않는다.

키 값은 `/health` 에도, 기동 실패 메시지에도 싣지 않는다(SEC-2).
"""

import base64

import pytest
from fastapi.testclient import TestClient

from main import app

KEY = base64.b64encode(bytes(range(32))).decode("ascii")


def test_키가_있으면_on_이다(monkeypatch):
    monkeypatch.setenv("TRANSCRIPT_ENC_KEY", KEY)
    with TestClient(app) as c:
        body = c.get("/health").json()
    assert body["transcript_encryption"] == "on"
    assert KEY not in str(body)


def test_키가_없으면_unset_이다(monkeypatch):
    """마스킹본 평문으로 저장 중이라는 뜻이다 — 운영에서 이 값이 보이면 시크릿에 키가 빠진 것이다."""
    monkeypatch.delenv("TRANSCRIPT_ENC_KEY", raising=False)
    with TestClient(app) as c:
        assert c.get("/health").json()["transcript_encryption"] == "unset"


def test_키_형식이_틀리면_서버가_뜨지_않는다(monkeypatch):
    """조용히 평문 저장으로 떨어지지 않는다 — 배포가 실패해 앞 파드가 그대로 남는 쪽이 낫다."""
    monkeypatch.setenv("TRANSCRIPT_ENC_KEY", "too-short")
    with pytest.raises(ValueError) as exc:
        with TestClient(app):
            pass
    assert "too-short" not in str(exc.value)
