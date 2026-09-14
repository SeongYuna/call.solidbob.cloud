# Requirement: J-4
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_dto import BlacklistEntry
from hub.app.dtos.blacklist_entry_list_dto import BlacklistEntryListQuery


class BlacklistEntryListUseCase(ABC):
    """관리자 블랙리스트 관리창 — 등록 에피소드 목록(최근 승인순)."""

    @abstractmethod
    async def list(self, query: BlacklistEntryListQuery) -> list[BlacklistEntry]: ...
