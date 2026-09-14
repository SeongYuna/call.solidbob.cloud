# Requirement: J-4, SEC-1
"""해제 인터랙터 — 사유를 확인·마스킹해 포트에 넘긴다. 사유 없는 해제를 받지 않는다(`decisions/205`)."""

from __future__ import annotations

from hub.app.dtos.blacklist_dto import BlacklistEntry
from hub.app.dtos.blacklist_release_dto import BlacklistReleaseCommand
from hub.app.ports.input.blacklist_release_use_case import BlacklistReleaseUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.ports.output.masking_port import MaskingPort

RELEASE_REASON_MAX_CHARS = 500  # `blacklist_entry.release_reason` VARCHAR(500)


class BlacklistReleaseInteractor(BlacklistReleaseUseCase):
    def __init__(self, blacklist: BlacklistPort, masking: MaskingPort) -> None:
        self._blacklist = blacklist
        self._masking = masking

    async def release(self, command: BlacklistReleaseCommand) -> BlacklistEntry:
        if not command.reason.strip():
            raise ValueError("해제 사유가 비어 있습니다")
        reason = self._masking.mask(command.reason.strip())[0][:RELEASE_REASON_MAX_CHARS]
        return await self._blacklist.release_entry(command.entry_id, released_by=command.released_by, reason=reason)
