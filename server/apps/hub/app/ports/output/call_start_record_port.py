# Requirement: 7.3절 전사 이벤트
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_start_dto import CallStarted


class CallStartRecordPort(ABC):
    """통화 시작 기록. `call` 행을 만든다. I/O 포트라 async (구현체도 async — LSP).

    이미 같은 `call_id` 가 있으면 건드리지 않고 False 를 돌려준다 — 게이트웨이가 재시도해도
    통화가 둘이 되거나 시작 시각이 덮이지 않는다."""

    @abstractmethod
    async def record(self, call: CallStarted) -> bool: ...
