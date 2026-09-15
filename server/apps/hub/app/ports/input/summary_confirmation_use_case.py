# Requirement: D-1, D-2, D-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.summary_confirmation_dto import SummaryConfirmationCommand, SummaryConfirmed


class SummaryConfirmationUseCase(ABC):
    """상담원이 통화 후 요약 초안을 고쳐서 확정한다. 확정은 한 번이다 — 다시 바꾸는 경로는 두지 않는다."""

    @abstractmethod
    async def confirm(self, command: SummaryConfirmationCommand) -> SummaryConfirmed: ...
