# Requirement: C-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_guard_check_dto import CallGuardCheckCommand, CallGuardCheckResult


class CallGuardCheckUseCase(ABC):
    """고객 발화 1건에서 폭언·위기 신호를 찾고 기록한다 (C-6).

    컴플라이언스(C-1~C-4, 상담원 발화)와 **별개 경로**다 — 한 인터랙터에 묶으면 화자로 분기하는 if 가 생긴다.
    """

    @abstractmethod
    async def check(self, command: CallGuardCheckCommand) -> CallGuardCheckResult: ...
