# Requirement: B-5, D-1, F-2
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_record_dto import CallRecord


class CallRecordUseCase(ABC):
    """상담기록 — 지난 통화의 요약·추천·필요서류 판정을 다시 본다. 실시간 경로가 아니다."""

    @abstractmethod
    async def get(self, call_id: str) -> CallRecord:
        """없는 통화면 `CallRecordNotFound`."""
