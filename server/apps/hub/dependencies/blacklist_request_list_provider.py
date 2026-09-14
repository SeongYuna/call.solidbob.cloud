# Requirement: J-4
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.blacklist_request_list_use_case import BlacklistRequestListUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.use_cases.blacklist_request_list_interactor import BlacklistRequestListInteractor
from hub.dependencies.blacklist_provider import get_blacklist_port


def get_blacklist_request_list_use_case(
    blacklist: BlacklistPort = Depends(get_blacklist_port),
) -> BlacklistRequestListUseCase:
    return BlacklistRequestListInteractor(blacklist=blacklist)
