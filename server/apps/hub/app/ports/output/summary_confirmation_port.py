# Requirement: D-1, D-2, D-3
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class SummaryConfirmationPort(ABC):
    """확정본을 남긴다 — `call.summary_text`·`inquiry_type`·`summary_confirmed_at` + `follow_up_action` 초안(draft)을 확정본(confirmed)으로 교체.

    **마스킹된 문자열만 받는다.** 통화가 없으면 `CallNotStartedError`, 이미 확정됐으면 `SummaryAlreadyConfirmedError`.
    """

    @abstractmethod
    async def confirm(
        self, call_id: str, *, summary_text: str, inquiry_type: str | None, follow_up_actions: tuple[str, ...]
    ) -> datetime:
        """확정 시각을 돌려준다."""
