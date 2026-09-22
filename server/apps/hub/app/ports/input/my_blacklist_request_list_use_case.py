# Requirement: J-2, J-4
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_dto import BlacklistRequest


class MyBlacklistRequestListUseCase(ABC):
    """상담원이 **자기가 올린** 전환 요청과 결과(상태·반려 사유)를 본다. 요청자는 토큰에서만 온다."""

    @abstractmethod
    async def list(self, requested_by: str) -> list[BlacklistRequest]: ...
