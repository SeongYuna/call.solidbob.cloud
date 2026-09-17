# Requirement: D-1, D-2
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_list_dto import CallListItem


class CallListPort(ABC):
    """저장된 통화를 읽는다. 통화 시작 기록 포트(`CallStartRecordPort`)와 가른 이유는 전사 조회와 같다 —
    쓰기는 콜 미디에이터가, 읽기는 상담원 화면이 한다."""

    @abstractmethod
    async def list_calls(self, limit: int, offset: int, customer_id: str | None) -> list[CallListItem]: ...

    @abstractmethod
    async def count_calls(self, customer_id: str | None) -> int: ...
