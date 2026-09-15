# Requirement: J-4, SEC-1
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_retention_dto import RetentionPurgeResult


class BlacklistRetentionPurgeUseCase(ABC):
    """보존 기간이 지난 블랙리스트 문장을 비운다 — 관리자가 부른다(`decisions/312`). 주기 실행은 아직 없다."""

    @abstractmethod
    async def purge(self) -> RetentionPurgeResult: ...
