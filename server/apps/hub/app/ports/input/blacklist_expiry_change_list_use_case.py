# Requirement: J-4
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_dto import ExpiryChange


class BlacklistExpiryChangeListUseCase(ABC):
    """등록 1건의 만료 변경 이력 — 관리자 감사 로그가 읽는다."""

    @abstractmethod
    async def list(self, entry_id: int) -> list[ExpiryChange]: ...
