# Requirement: D-1, D-2, D-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.summary_revision_dto import SummaryRevision


class SummaryRevisionListUseCase(ABC):
    """한 통화의 요약 재수정 이력 — 무엇이 어떻게 바뀌었는지."""

    @abstractmethod
    async def list(self, call_id: str) -> list[SummaryRevision]: ...
