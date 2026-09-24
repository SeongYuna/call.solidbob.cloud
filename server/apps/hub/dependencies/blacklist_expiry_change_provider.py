# Requirement: J-4
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.blacklist_expiry_change_list_use_case import BlacklistExpiryChangeListUseCase
from hub.app.ports.input.blacklist_expiry_change_recent_use_case import BlacklistRecentExpiryChangeUseCase
from hub.app.ports.input.blacklist_expiry_change_use_case import BlacklistExpiryChangeUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.use_cases.blacklist_expiry_change_interactor import BlacklistExpiryChangeInteractor
from hub.app.use_cases.blacklist_expiry_change_list_interactor import BlacklistExpiryChangeListInteractor
from hub.app.use_cases.blacklist_expiry_change_recent_interactor import BlacklistRecentExpiryChangeInteractor
from hub.dependencies.blacklist_provider import get_blacklist_port
from hub.dependencies.masking_provider import get_masking_port


def get_blacklist_expiry_change_use_case(
    blacklist: BlacklistPort = Depends(get_blacklist_port),
    masking: MaskingPort = Depends(get_masking_port),
) -> BlacklistExpiryChangeUseCase:
    return BlacklistExpiryChangeInteractor(blacklist=blacklist, masking=masking)


def get_blacklist_expiry_change_list_use_case(
    blacklist: BlacklistPort = Depends(get_blacklist_port),
) -> BlacklistExpiryChangeListUseCase:
    return BlacklistExpiryChangeListInteractor(blacklist=blacklist)


def get_blacklist_recent_expiry_change_use_case(
    blacklist: BlacklistPort = Depends(get_blacklist_port),
) -> BlacklistRecentExpiryChangeUseCase:
    return BlacklistRecentExpiryChangeInteractor(blacklist=blacklist)
