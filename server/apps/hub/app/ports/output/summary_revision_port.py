# Requirement: D-1, D-2, D-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.summary_revision_dto import SummaryRevision


class SummaryNotConfirmedError(Exception):
    """아직 확정되지 않은 요약이다 — 재수정이 아니라 확정(`…/summary-confirmation`)을 먼저 한다."""

    def __init__(self, call_id: str) -> None:
        super().__init__(call_id)
        self.call_id = call_id


class SummaryRevisionPort(ABC):
    """확정된 요약을 고친다 — 이전 요약·유형을 `call_summary_revision` 에 쌓고 `call` 을 새 값으로,
    후속조치는 `confirmed` 를 `superseded` 로 남기고 새 것을 `confirmed` 로 넣는다. **지우지 않는다.**

    **마스킹된 문자열만 받는다.** 통화가 없으면 `CallNotStartedError`, 확정 전이면 `SummaryNotConfirmedError`.
    """

    @abstractmethod
    async def revise(
        self, call_id: str, *, summary_text: str, inquiry_type: str | None, follow_up_actions: tuple[str, ...], reason: str
    ) -> SummaryRevision: ...

    @abstractmethod
    async def list_revisions(self, call_id: str) -> list[SummaryRevision]:
        """오래된 순. 통화가 없으면 `CallNotStartedError`."""
