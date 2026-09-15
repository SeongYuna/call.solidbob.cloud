# Requirement: B-5, D-1, F-2
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_record_dto import CallRecord


class CallRecordPort(ABC):
    """통화 1건의 저장 기록을 읽는다. 없는 통화면 None. 추천은 만든 순서, 카드는 rank 순, 판정은 판정 순이다."""

    @abstractmethod
    async def get(self, call_id: str) -> CallRecord | None: ...
