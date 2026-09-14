# Requirement: D-1, D-2
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_list_dto import CallListPage, CallListQuery


class CallListUseCase(ABC):
    """지난 통화 목록 — 상담기록 패널이 최근 시작순으로 본다. 실시간 경로가 아니다."""

    @abstractmethod
    async def list(self, query: CallListQuery) -> CallListPage: ...
