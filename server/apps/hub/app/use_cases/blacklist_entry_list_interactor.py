# Requirement: J-4
"""등록 목록 인터랙터 — 포트를 부르는 것이 전부다. 「재범」 같은 분류를 여기서 만들지 않는다(화면 몫)."""

from __future__ import annotations

from hub.app.dtos.blacklist_dto import BlacklistEntry
from hub.app.dtos.blacklist_entry_list_dto import BlacklistEntryListQuery
from hub.app.ports.input.blacklist_entry_list_use_case import BlacklistEntryListUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort


class BlacklistEntryListInteractor(BlacklistEntryListUseCase):
    def __init__(self, blacklist: BlacklistPort) -> None:
        self._blacklist = blacklist

    async def list(self, query: BlacklistEntryListQuery) -> list[BlacklistEntry]:
        return await self._blacklist.list_entries(active_only=query.active_only)
