# Requirement: J-4
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.blacklist_entry_list_use_case import BlacklistEntryListUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.use_cases.blacklist_entry_list_interactor import BlacklistEntryListInteractor
from hub.dependencies.blacklist_provider import get_blacklist_port


def get_blacklist_entry_list_use_case(
    blacklist: BlacklistPort = Depends(get_blacklist_port),
) -> BlacklistEntryListUseCase:
    return BlacklistEntryListInteractor(blacklist=blacklist)
