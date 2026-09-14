# Requirement: C-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_guard_flag_list_dto import CallGuardFlagListQuery, CallGuardFlagPage


class CallGuardFlagListUseCase(ABC):
    """관리자가 콜 가드 신호 기록을 최근순으로 본다. 집계·점수는 만들지 않는다(부록 A-1)."""

    @abstractmethod
    async def list(self, query: CallGuardFlagListQuery) -> CallGuardFlagPage: ...
