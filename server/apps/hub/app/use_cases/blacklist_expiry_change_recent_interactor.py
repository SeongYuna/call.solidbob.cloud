# Requirement: J-4
from __future__ import annotations

from hub.app.dtos.blacklist_dto import ExpiryChange
from hub.app.ports.input.blacklist_expiry_change_recent_use_case import BlacklistRecentExpiryChangeUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort


class BlacklistRecentExpiryChangeInteractor(BlacklistRecentExpiryChangeUseCase):
    def __init__(self, blacklist: BlacklistPort) -> None:
        self._blacklist = blacklist

    async def recent(self, limit: int) -> list[ExpiryChange]:
        return await self._blacklist.list_recent_expiry_changes(limit)
