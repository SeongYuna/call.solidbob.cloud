# Requirement: QUA-1
"""합성 루트 테스트 공통 — `dependency_overrides` 는 앱 전역이라 테스트 사이에 샌다.

`test_main_health` 가 `es.internal` 검색 클라이언트를 꽂아 두면 다음 테스트가 그 주소로 검색을
시도한다(2026-09-10 트리거 배선 뒤 드러났다 — 전에는 트리거 501 이 먼저 막아 보이지 않았다).
"""

import pytest

from main import app


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
