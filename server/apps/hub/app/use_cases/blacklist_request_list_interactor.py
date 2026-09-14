# Requirement: J-4
"""요청 목록 인터랙터. 상태 값만 확인하고 포트를 부른다 — 정렬은 리포지토리가 한다."""

from __future__ import annotations

from hub.app.dtos.blacklist_dto import STATUSES, BlacklistRequest
from hub.app.dtos.blacklist_request_list_dto import BlacklistRequestListQuery
from hub.app.ports.input.blacklist_request_list_use_case import BlacklistRequestListUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort


class BlacklistRequestListInteractor(BlacklistRequestListUseCase):
    def __init__(self, blacklist: BlacklistPort) -> None:
        self._blacklist = blacklist

    async def list(self, query: BlacklistRequestListQuery) -> list[BlacklistRequest]:
        if query.status is not None and query.status not in STATUSES:
            raise ValueError(f"'{query.status}' 는 요청 상태가 아닙니다 (가능: {', '.join(STATUSES)})")
        return await self._blacklist.list_requests(query.status)
