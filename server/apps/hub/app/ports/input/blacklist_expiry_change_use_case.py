# Requirement: J-4
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_expiry_change_dto import BlacklistExpiryChangeCommand, BlacklistExpiryChanged


class BlacklistExpiryChangeUseCase(ABC):
    """관리자가 등록 만료를 늘리거나 줄인다. 사유 필수 · 이력이 쌓인다(`decisions/309`)."""

    @abstractmethod
    async def change(self, command: BlacklistExpiryChangeCommand) -> BlacklistExpiryChanged: ...
