# Requirement: D-1, D-2, D-3
"""HTTP 표면 스키마. 필드명은 db `call.summary_text`·`call.inquiry_type`·`follow_up_action.action_text` 와 같다."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ._types import StrField


class TranscriptSegmentInput(BaseModel):
    """마스킹 완료본만 (SEC-1). 원문 필드가 없다."""

    segment_id: int
    speaker: Literal["customer", "agent"]
    text: str
    is_final: bool = True
    utterance_end_ms: int | None = None


class PostcallRequest(BaseModel):
    call_id: str
    segments: list[TranscriptSegmentInput] = Field(min_length=1)


class FollowUpActionSchema(BaseModel):
    action_text: str


class CallSummaryResponse(BaseModel):
    call_id: str
    summary_text: str = Field(description="D-1 상담 요약 — 초안")
    inquiry_type: str | None = Field(default=None, description="D-2 분류 **제안**. 확정 아님 — 상담원이 바꾼다")
    follow_up_actions: list[FollowUpActionSchema] = Field(description="D-3 후속조치 초안")
    confirmed: StrField = Field(description="상담원 확정 여부. 생성 직후에는 항상 false")
