# Requirement: J-4
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_dto import BlacklistRequest
from hub.app.dtos.blacklist_request_list_dto import BlacklistRequestListQuery


class BlacklistRequestListUseCase(ABC):
    """관리자 승인요청창이 읽는 요청 목록(최근 요청순)."""

    @abstractmethod
    async def list(self, query: BlacklistRequestListQuery) -> list[BlacklistRequest]: ...
