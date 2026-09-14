# Requirement: J-4, SEC-1, QUA-1
import asyncio

import pytest

from hub.app.dtos.blacklist_release_dto import BlacklistReleaseCommand
from hub.app.use_cases.blacklist_release_interactor import BlacklistReleaseInteractor

from ._blacklist_stubs import DigitMasking, StubBlacklist


def test_사유를_마스킹해_해제한다():
    blacklist = StubBlacklist()
    entry = asyncio.run(BlacklistReleaseInteractor(blacklist, DigitMasking()).release(
        BlacklistReleaseCommand(entry_id=3, released_by="admin-1", reason="오인 신고 010-1234-5678")))
    assert blacklist.calls == [("release", 3, "admin-1", "오인 신고 ***-****-****")]
    assert entry.released_by == "admin-1"


def test_사유_없는_해제는_거부한다():
    blacklist = StubBlacklist()
    with pytest.raises(ValueError):
        asyncio.run(BlacklistReleaseInteractor(blacklist, DigitMasking()).release(
            BlacklistReleaseCommand(entry_id=3, released_by="admin-1", reason=" ")))
    assert blacklist.calls == []
