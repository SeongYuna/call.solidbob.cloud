# Requirement: E-1
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ._types import StrField


class CardFeedbackRequest(BaseModel):
    action: Literal["adopted", "ignored"] = Field(description="상담원이 이 카드를 썼는지")
    # agent_id 를 받지 않는다 — 상담원 단위 집계를 만들 수 없게 하기 위해서다 (부록 A-1)


class CardFeedbackResponse(BaseModel):
    """값은 전부 문자열(2026-09-10 합의) — 이 응답만 정수로 남아 있었다(2026-09-15 정정)."""

    feedback_id: StrField
    card_id: StrField
    action: Literal["adopted", "ignored"]
