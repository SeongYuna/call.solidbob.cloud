# Requirement: D-1, D-2, D-3
"""HTTP 표면 스키마 — 확정된 요약 재수정과 그 이력. 값은 전부 문자열이다(`_types.StrField`)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField

from hub.app.dtos.summary_revision_dto import SummaryRevision


class SummaryRevisionRequest(BaseModel):
    summary_text: str = Field(min_length=1, max_length=5000, description="새 요약. 저장 전 마스킹")
    reason: str = Field(min_length=1, max_length=2000, description="왜 고치는가(필수). 저장 전 마스킹, 500자")
    inquiry_type: str | None = Field(default=None, max_length=30)
    follow_up_actions: list[str] = Field(default_factory=list, max_length=20, description="새 확정 후속조치. 이전 것은 superseded 로 남는다")


class SummaryRevisionItemSchema(BaseModel):
    revision_id: StrField
    call_id: str
    previous_summary_text: str = Field(description="고치기 전 요약(마스킹본)")
    previous_inquiry_type: str | None = None
    reason: str = Field(description="마스킹된 사유")
    revised_at: str

    @staticmethod
    def from_dto(r: SummaryRevision) -> "SummaryRevisionItemSchema":
        return SummaryRevisionItemSchema(revision_id=r.revision_id, call_id=r.call_id,
                                         previous_summary_text=r.previous_summary_text,
                                         previous_inquiry_type=r.previous_inquiry_type, reason=r.reason,
                                         revised_at=r.revised_at.isoformat())


class SummaryRevisedResponse(BaseModel):
    call_id: str
    summary_text: str
    inquiry_type: str | None = None
    follow_up_actions: list[str]
    revision: SummaryRevisionItemSchema


class SummaryRevisionListResponse(BaseModel):
    revisions: list[SummaryRevisionItemSchema] = Field(description="오래된 순")
