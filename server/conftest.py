# Requirement: QUA-1, SEC-2
"""테스트 환경 격리.

**테스트는 주변 환경에 기대지 않는다.** 여러 테스트가 "PostgreSQL 이 설정되지 않았을 때
501 을 준다" 를 확인하는데, `.env` 를 export 한 셸에서 돌리면 그 전제가 깨져 **6건이
빨간불**이 된다. CI 는 `.env` 가 없어 통과하므로 **로컬에서만 나는 유령 실패**가 되고,
받은 사람은 자기 환경을 의심하며 시간을 쓴다(2026-08-27 실제로 겪었다).

그래서 설정 계열 환경변수를 테스트마다 걷어낸다. 실제 DB 가 필요한
`@pytest.mark.integration` 테스트는 **`integration_settings` 픽스처로 명시적으로** 설정을 다시
가져간다 — 필요한 쪽이 명시적으로 가져가는 구조다.
"""

from __future__ import annotations

import os

import pytest

# `core/config.py` 가 읽는 접두어들. 설정을 읽는 곳이 거기 하나뿐이라 목록이 짧게 유지된다.
_MANAGED_PREFIXES = ("POSTGRES_", "DATABASE_", "ELASTICSEARCH_", "GOOGLE_", "STT_", "AWS_")

# integration 테스트 전용 DB. 위 접두어에 걸리지 않는 이름이라 격리 픽스처가 걷어내지 않는다.
# CI(`test.yml` 의 `server` job)가 매번 새로 띄운 PostgreSQL 에 현재 `db/schema.sql` 을 넣고 여기에 준다.
TEST_DATABASE_URL_ENV = "CALLGUARD_TEST_DATABASE_URL"


@pytest.fixture(autouse=True)
def isolated_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """설정 환경변수를 걷어낸 상태에서 각 테스트를 돌린다."""
    for key in list(os.environ):
        if key.startswith(_MANAGED_PREFIXES):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def integration_settings(isolated_settings_env, monkeypatch: pytest.MonkeyPatch):
    """실제 PostgreSQL 이 필요한 테스트의 설정. **`CALLGUARD_TEST_DATABASE_URL` 하나만 본다.**
    없으면 스킵한다 — 없는 DB 를 만들어내지 않는다.

    **루트 `.env` 는 읽지 않는다.** 이 테스트들은 행을 쓰고 지운다. `.env` 의 DB 는 개발 공유 DB·운영 DB
    일 수 있고, 2026-09-11 에는 쓰지 않기로 한 Neon(옛 스키마)이었다. 테스트가 쓸 DB 는 사람이 골라서 준다
    — 현재 `db/schema.sql` 을 넣은 새 DB 를 권한다(`server/CLAUDE.md` §4).

    전에는 이 로직이 테스트 파일 셋에 `_settings()` 로 복사돼 있었고 `.env` 만 읽어서, `.env` 가 없는
    CI 에서는 **한 번도 돌지 않고 전부 스킵**됐다. 스키마(PK `(call_id, segment_id)`)와 전사 저장
    어댑터가 사흘간 어긋나 있어도 초록이었던 이유다.
    """
    test_url = os.environ.get(TEST_DATABASE_URL_ENV)
    if not test_url:
        pytest.skip(f"{TEST_DATABASE_URL_ENV} 가 없다 — 현재 db/schema.sql 을 넣은 DB 주소를 준다")
    monkeypatch.setenv("DATABASE_URL", test_url)

    from core.config import load_settings  # noqa: PLC0415 — 위 환경을 채운 뒤에 읽어야 한다

    return load_settings()
