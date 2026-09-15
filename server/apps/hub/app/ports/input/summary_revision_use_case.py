# Requirement: D-1, D-2, D-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.summary_revision_dto import SummaryRevisionCommand, SummaryRevised


class SummaryRevisionUseCase(ABC):
    """확정된 요약을 사유와 함께 고친다. 고치기 전 값은 이력으로 남는다."""

    @abstractmethod
    async def revise(self, command: SummaryRevisionCommand) -> SummaryRevised: ...
