# Requirement: SEC-2, QUA-1
"""쓰기 경로 문이 fail-closed 라(`decisions/120` 4번) 라우터 테스트마다 서비스 토큰을 설정해 둔다 — `_ingest_auth.py`."""

import pytest

from hub.tests.adapter._ingest_auth import TOKEN


@pytest.fixture(autouse=True)
def _ingest_service_token(monkeypatch):
    monkeypatch.setenv("INGEST_SERVICE_TOKEN", TOKEN)
