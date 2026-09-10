# Requirement: [Task 1], SEC-2, QUA-1
"""앱이 뜨고 /health 가 설정 '여부'만 알리는지 — 값(호스트·비밀번호·URL)이 응답에 새지 않는지."""

import importlib.util

import pytest
from fastapi.testclient import TestClient

from main import app

# `ai/` 검색 구현은 `elasticsearch` 패키지가 있어야 꽂힌다. server CI 는 그걸 설치하지
# 않으므로(`server/requirements.txt` 에 없다) 환경에 따라 스포크 수가 달라진다.
# **테스트가 로컬 환경을 전제하면 CI 에서만 깨진다** — 2026-08-27 실제로 겪었다.
AI_RETRIEVAL_AVAILABLE = importlib.util.find_spec("elasticsearch") is not None


def test_health_reports_configured_flags_without_values(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:secret-pw@db.internal:5432/callguard")
    monkeypatch.setenv("ELASTICSEARCH_URL", "http://es.internal:9200")
    with TestClient(app) as client:
        body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["postgres_configured"] is True and body["elasticsearch_configured"] is True
    # 규칙 기반 스포크는 언제나 붙는다. 검색은 `elasticsearch` 패키지가 있을 때만 —
    # 없으면 조용히 501 로 남는 것이 설계다(`_project/decisions/024`).
    assert body["spokes"][:2] == ["masking", "closure_gate"]
    dumped = str(body)
    assert "secret-pw" not in dumped and "db.internal" not in dumped and "es.internal" not in dumped


def test_health_when_nothing_configured(monkeypatch):
    for k in ("DATABASE_URL", "MYSQL_HOST", "MYSQL_DB_NAME", "MYSQL_USER", "MYSQL_PASSWORD", "ELASTICSEARCH_URL"):
        monkeypatch.delenv(k, raising=False)
    with TestClient(app) as client:
        body = client.get("/health").json()
    assert body["postgres_configured"] is False and body["elasticsearch_configured"] is False
    # 규칙 기반 스포크는 외부 자원이 없어도 붙는다. 검색은 ES 가 없으면 안 붙고 501 로 남는다.
    # 트리거(B-1)는 외부 자원이 없어 `ai/` 만 있으면 붙는다 — 그래서 앞 둘만 고정한다.
    assert body["spokes"][:2] == ["masking", "closure_gate"]
    assert "retrieval" not in body["spokes"]


@pytest.mark.skipif(not AI_RETRIEVAL_AVAILABLE, reason="elasticsearch 패키지 없음 — 검색 스포크가 안 꽂힌다")
def test_ES가_설정되면_검색_스포크가_꽂힌다(monkeypatch):
    """`decisions/024` — 합성 루트가 `ai/` 구현을 요청 경로에 꽂는다."""
    monkeypatch.setenv("ELASTICSEARCH_URL", "http://es.internal:9200")
    with TestClient(app) as client:
        assert "retrieval" in client.get("/health").json()["spokes"]


def test_ES가_없으면_검색_스포크가_안_꽂힌다(monkeypatch):
    """임시 구현을 만들지 않는다 — 빈 목록은 「관련 문서 없음」(B-6)과 구분되지 않는다."""
    monkeypatch.delenv("ELASTICSEARCH_URL", raising=False)
    with TestClient(app) as client:
        assert "retrieval" not in client.get("/health").json()["spokes"]


def test_스포크_목록이_설정_값을_흘리지_않는다(monkeypatch):
    """`/health` 는 설정 '여부'만 알린다(SEC-2). 스포크 이름에 URL·인덱스명이 섞이면 안 된다."""
    monkeypatch.setenv("ELASTICSEARCH_URL", "http://es.internal:9200")
    with TestClient(app) as client:
        spokes = client.get("/health").json()["spokes"]
    assert all(s.isidentifier() for s in spokes), f"스포크 이름이 식별자가 아니다: {spokes}"
