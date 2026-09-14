# Requirement: C-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_guard_flag_list_dto import CallGuardFlagRecord


class CallGuardFlagQueryPort(ABC):
    """저장된 콜 가드 신호를 읽는다. 기록 포트(`CallGuardFlagRecordPort`)와 가른 이유는 전사 조회와 같다."""

    @abstractmethod
    async def list_flags(
        self, call_id: str | None, category: str | None, limit: int, offset: int
    ) -> list[CallGuardFlagRecord]: ...

    @abstractmethod
    async def count_flags(self, call_id: str | None, category: str | None) -> int: ...
