# Requirement: SEC-2, QUA-1
"""커넥션 문자열이 설정에서 어떻게 만들어지는지 — 실제 DB 없이 고정한다.

운영(k3s)은 `DATABASE_URL` **하나만** 주입한다(`docs/infra-runbook.md` 12-2 · 16-1). 개별
`POSTGRES_*` 만 읽으면 `/health` 는 `postgres_configured: true` 인데 실제 연결은 호스트 없이
시도돼 실패한다 — 2026-09-10 확인. 그래서 `DATABASE_URL` 이 있으면 그것을 쓴다.
"""

import pytest

from core.config import Settings
from hub.adapter.outbound.postgres.connection import build_connection_factory, conninfo_for


def _settings(**over) -> Settings:
    base = dict(
        postgres_host=None, postgres_port=5432, postgres_db_name=None, postgres_user=None,
        postgres_password=None, database_url=None, elasticsearch_url=None, elasticsearch_api_key=None,
        huggingface_token=None, cors_allowed_origins=(),
    )
    return Settings(**{**base, **over})


def test_DATABASE_URL이_있으면_그대로_쓴다():
    url = "postgresql://u:pw@db.internal:5432/callguard?sslmode=require"
    assert conninfo_for(_settings(database_url=url)) == url


def test_DATABASE_URL이_없으면_개별_키로_조립한다():
    info = conninfo_for(_settings(
        postgres_host="127.0.0.1", postgres_db_name="callguard", postgres_user="cg", postgres_password="pw",
    ))
    assert "host=127.0.0.1" in info and "dbname=callguard" in info and "user=cg" in info and "password=pw" in info


def test_둘_다_있으면_DATABASE_URL이_이긴다():
    """운영 주입 방식이 정본이다. 개별 키는 로컬 편의용이라 뒤로 간다."""
    url = "postgresql://u:pw@db.internal:5432/callguard"
    info = conninfo_for(_settings(database_url=url, postgres_host="127.0.0.1", postgres_db_name="x",
                                  postgres_user="y", postgres_password="z"))
    assert info == url


def test_설정이_없으면_팩토리를_만들지_않는다():
    with pytest.raises(RuntimeError):
        build_connection_factory(_settings())
