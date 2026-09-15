# Requirement: J-4, QUA-1
from datetime import datetime, timedelta, timezone

from blacklist.domain.services.retention import PURGED_TEXT, RETENTION_DAYS, purge_cutoff

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)


def test_끝난_지_180일이_기준이다():
    assert RETENTION_DAYS == 180
    assert purge_cutoff(NOW) == NOW - timedelta(days=180)


def test_비운_표시는_빈_문자열이_아니다():
    """NOT NULL 컬럼 — 「원래 비어 있었다」 와 「보존 기간이 지나 비웠다」 를 구분한다."""
    assert PURGED_TEXT.strip()
