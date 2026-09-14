# Requirement: J-4, QUA-1
import asyncio

from hub.app.dtos.blacklist_entry_list_dto import BlacklistEntryListQuery
from hub.app.use_cases.blacklist_entry_list_interactor import BlacklistEntryListInteractor

from ._blacklist_stubs import StubBlacklist


def test_적용_중만_볼지를_포트에_넘긴다():
    blacklist = StubBlacklist()
    asyncio.run(BlacklistEntryListInteractor(blacklist).list(BlacklistEntryListQuery(active_only=True)))
    asyncio.run(BlacklistEntryListInteractor(blacklist).list(BlacklistEntryListQuery()))
    assert blacklist.calls == [("list_entries", True), ("list_entries", False)]
