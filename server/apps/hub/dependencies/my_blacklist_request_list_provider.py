# Requirement: J-2, J-4
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.my_blacklist_request_list_use_case import MyBlacklistRequestListUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.use_cases.my_blacklist_request_list_interactor import MyBlacklistRequestListInteractor
from hub.dependencies.blacklist_provider import get_blacklist_port


def get_my_blacklist_request_list_use_case(
    blacklist: BlacklistPort = Depends(get_blacklist_port),
) -> MyBlacklistRequestListUseCase:
    return MyBlacklistRequestListInteractor(blacklist=blacklist)
