# Requirement: J-4, QUA-1
import asyncio

import pytest

from hub.app.dtos.blacklist_request_list_dto import BlacklistRequestListQuery
from hub.app.use_cases.blacklist_request_list_interactor import BlacklistRequestListInteractor

from ._blacklist_stubs import StubBlacklist


def test_상태_필터를_포트에_넘긴다():
    blacklist = StubBlacklist()
    asyncio.run(BlacklistRequestListInteractor(blacklist).list(BlacklistRequestListQuery(status="pending")))
    assert blacklist.calls == [("list_requests", "pending")]


def test_없는_상태는_거부한다():
    """`released` 는 요청이 아니라 등록의 상태다(`decisions/205` ②)."""
    blacklist = StubBlacklist()
    with pytest.raises(ValueError):
        asyncio.run(BlacklistRequestListInteractor(blacklist).list(BlacklistRequestListQuery(status="released")))
    assert blacklist.calls == []
