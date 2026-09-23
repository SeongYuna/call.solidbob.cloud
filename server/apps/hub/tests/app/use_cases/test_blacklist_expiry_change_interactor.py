# Requirement: J-4, SEC-1, QUA-1
"""만료 변경: 지금부터 N일 뒤로 · 사유 마스킹 · 범위 밖·빈 사유 거부(포트를 부르지 않는다)."""

import asyncio
from datetime import timedelta

import pytest

from hub.app.dtos.blacklist_expiry_change_dto import BlacklistExpiryChangeCommand
from hub.app.use_cases.blacklist_expiry_change_interactor import BlacklistExpiryChangeInteractor

from ._blacklist_stubs import NOW, DigitMasking, StubBlacklist


def _change(blacklist, days=30, reason="재발 우려 010-1234-5678"):
    return asyncio.run(BlacklistExpiryChangeInteractor(blacklist, DigitMasking(), now=lambda: NOW).change(
        BlacklistExpiryChangeCommand(entry_id=3, changed_by="admin-1", expires_in_days=days, reason=reason)))


def test_지금부터_N일_뒤로_바꾸고_사유를_마스킹한다():
    blacklist = StubBlacklist()
    changed = _change(blacklist, days=90)
    assert blacklist.calls == [("change_expiry", 3, "admin-1", NOW + timedelta(days=90), "재발 우려 ***-****-****")]
    assert changed.change.new_expires_at == NOW + timedelta(days=90)


def test_하루짜리_단축도_같은_경로다():
    blacklist = StubBlacklist()
    _change(blacklist, days=1)
    assert blacklist.calls[0][3] == NOW + timedelta(days=1)


@pytest.mark.parametrize("days", [0, 366, -5])
def test_범위_밖_일수는_거부한다(days):
    blacklist = StubBlacklist()
    with pytest.raises(ValueError):
        _change(blacklist, days=days)
    assert blacklist.calls == []


def test_사유_없는_변경은_거부한다():
    blacklist = StubBlacklist()
    with pytest.raises(ValueError):
        _change(blacklist, reason="   ")
    assert blacklist.calls == []


def test_감사_로그용_최근_이력은_한도를_그대로_저장소에_넘긴다():
    """인터랙터는 판정하지 않는다 — 자르는 일은 저장소(SQL `LIMIT`)가 한다(`w6-audit-log-blacklist-reset`)."""
    import asyncio

    from hub.app.use_cases.blacklist_expiry_change_recent_interactor import BlacklistRecentExpiryChangeInteractor

    blacklist = StubBlacklist()
    assert asyncio.run(BlacklistRecentExpiryChangeInteractor(blacklist=blacklist).recent(50)) == []
    assert blacklist.calls == [("list_recent_expiry_changes", 50)]
