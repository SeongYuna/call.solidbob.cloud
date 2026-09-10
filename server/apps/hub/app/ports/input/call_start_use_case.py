# Requirement: 7.3절 전사 이벤트
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_start_dto import CallStartCommand, CallStarted


class CallStartUseCase(ABC):
    """통화 시작 알림 → `call` 행 생성. 같은 `call_id` 를 다시 받아도 실패하지 않는다(멱등)."""

    @abstractmethod
    async def start(self, command: CallStartCommand) -> CallStarted: ...
