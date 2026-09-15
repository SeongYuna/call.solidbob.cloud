# Requirement: J-4, SEC-1
"""보존 기간 정리 인터랙터 — 포트를 부르는 것이 전부다. 무엇이 기간을 넘었는지는 규칙(블랙리스트 도메인)이 정한다."""

from __future__ import annotations

from hub.app.dtos.blacklist_retention_dto import RetentionPurgeResult
from hub.app.ports.input.blacklist_retention_purge_use_case import BlacklistRetentionPurgeUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort


class BlacklistRetentionPurgeInteractor(BlacklistRetentionPurgeUseCase):
    def __init__(self, blacklist: BlacklistPort) -> None:
        self._blacklist = blacklist

    async def purge(self) -> RetentionPurgeResult:
        return await self._blacklist.purge_retained_texts()
