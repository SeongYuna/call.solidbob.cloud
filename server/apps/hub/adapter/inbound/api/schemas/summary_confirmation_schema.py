# Requirement: D-1, D-2, D-3
"""HTTP 표면 스키마 — 통화 후 요약 확정. 값은 전부 문자열이다(`_types.StrField`)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField


class SummaryConfirmationRequest(BaseModel):
    summary_text: str = Field(min_length=1, max_length=5000, description="상담원이 고친(또는 그대로 둔) 요약. 저장 전 마스킹")
    inquiry_type: str | None = Field(default=None, max_length=30, description="상담원이 정한 유형(선택)")
    follow_up_actions: list[str] = Field(default_factory=list, max_length=20, description="확정할 후속조치 문구. 초안(draft)은 이것으로 교체된다")


class SummaryConfirmedResponse(BaseModel):
    call_id: str
    summary_text: str = Field(description="마스킹된 저장본")
    inquiry_type: str | None = None
    follow_up_actions: list[str]
    confirmed: StrField = Field(description="늘 true")
    confirmed_at: str
