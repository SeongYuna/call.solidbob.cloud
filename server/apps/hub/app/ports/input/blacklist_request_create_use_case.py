# Requirement: J-1, J-2
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_request_create_dto import BlacklistRequestCreateCommand, BlacklistRequestCreated


class BlacklistRequestCreateUseCase(ABC):
    """상담원이 블랙리스트 전환을 **요청**한다. 등록이 아니다 — 관리자가 결정한다(`decisions/204`)."""

    @abstractmethod
    async def create(self, command: BlacklistRequestCreateCommand) -> BlacklistRequestCreated: ...
