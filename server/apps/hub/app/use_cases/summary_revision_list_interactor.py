# Requirement: D-1, D-2, D-3
from __future__ import annotations

from hub.app.dtos.summary_revision_dto import SummaryRevision
from hub.app.ports.input.summary_revision_list_use_case import SummaryRevisionListUseCase
from hub.app.ports.output.summary_revision_port import SummaryRevisionPort


class SummaryRevisionListInteractor(SummaryRevisionListUseCase):
    def __init__(self, revisions: SummaryRevisionPort) -> None:
        self._revisions = revisions

    async def list(self, call_id: str) -> list[SummaryRevision]:
        return await self._revisions.list_revisions(call_id)
