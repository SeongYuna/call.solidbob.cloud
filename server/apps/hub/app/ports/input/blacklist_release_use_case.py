# Requirement: J-4
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_dto import BlacklistEntry
from hub.app.dtos.blacklist_release_dto import BlacklistReleaseCommand


class BlacklistReleaseUseCase(ABC):
    """관리자가 등록 에피소드를 해제한다. 지우지 않는다 — 왜 풀렸는지가 남는다."""

    @abstractmethod
    async def release(self, command: BlacklistReleaseCommand) -> BlacklistEntry: ...
