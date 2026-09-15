# Requirement: D-1, D-2, D-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_summary_dto import CallSummaryDraft


class SummaryAlreadyConfirmedError(Exception):
    """상담원이 이미 확정한 요약이다 — 초안으로 덮지 않는다(부록 A-1: 사람이 정한 것을 모델 출력이 되돌리면 안 된다)."""

    def __init__(self, call_id: str) -> None:
        super().__init__(call_id)
        self.call_id = call_id


class PostcallRecordPort(ABC):
    """통화 후 **초안**을 남긴다 — `call.summary_text`·`call.inquiry_type` + `follow_up_action`(status `draft`).

    `call.summary_confirmed_at` 은 건드리지 않는다 — NULL 이 곧 «초안» 이다(`decisions/205` ⑧).
    같은 통화를 다시 닫으면 확정 전 초안은 새 초안으로 바뀐다.
    """

    @abstractmethod
    async def record(self, draft: CallSummaryDraft) -> None:
        """통화가 없으면 `CallNotStartedError`, 이미 확정됐으면 `SummaryAlreadyConfirmedError`.
        저장소가 둘을 모르면(로그 어댑터) 올리지 않는다."""
