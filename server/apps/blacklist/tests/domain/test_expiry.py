# Requirement: J-4, QUA-1
"""누적 상한 — 승인일 + 365일까지만. 경계는 허용, 1초라도 넘으면 거부."""

from datetime import datetime, timedelta, timezone

from blacklist.domain.services.expiry import MAX_DAYS_FROM_APPROVAL, latest_allowed_expiry, within_cap

APPROVED = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def test_상한은_승인일로부터_365일이다():
    assert MAX_DAYS_FROM_APPROVAL == 365
    assert latest_allowed_expiry(APPROVED) == APPROVED + timedelta(days=365)


def test_경계는_허용하고_넘으면_거부한다():
    assert within_cap(APPROVED, APPROVED + timedelta(days=365)) is True
    assert within_cap(APPROVED, APPROVED + timedelta(days=365, seconds=1)) is False


def test_단축은_늘_통과한다():
    assert within_cap(APPROVED, APPROVED + timedelta(days=1)) is True
