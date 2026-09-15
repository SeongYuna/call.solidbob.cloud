# Requirement: J-4
from __future__ import annotations

from hub.app.dtos.blacklist_dto import ExpiryChange
from hub.app.ports.input.blacklist_expiry_change_list_use_case import BlacklistExpiryChangeListUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort


class BlacklistExpiryChangeListInteractor(BlacklistExpiryChangeListUseCase):
    def __init__(self, blacklist: BlacklistPort) -> None:
        self._blacklist = blacklist

    async def list(self, entry_id: int) -> list[ExpiryChange]:
        return await self._blacklist.list_expiry_changes(entry_id)
