# Requirement: J-2, J-4
"""「내 요청」 인터랙터 — 판정 없음. 요청자로 걸러 포트를 부른다(최근 요청순은 리포지토리가 정한다)."""

from __future__ import annotations

from hub.app.dtos.blacklist_dto import BlacklistRequest
from hub.app.ports.input.my_blacklist_request_list_use_case import MyBlacklistRequestListUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort


class MyBlacklistRequestListInteractor(MyBlacklistRequestListUseCase):
    def __init__(self, blacklist: BlacklistPort) -> None:
        self._blacklist = blacklist

    async def list(self, requested_by: str) -> list[BlacklistRequest]:
        return await self._blacklist.list_requests(requested_by=requested_by)
