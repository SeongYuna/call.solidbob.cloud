# Requirement: A-1, SEC-1
"""HTTP 표면 스키마. 전사 이벤트 필드명은 7.3절 계약과 같다."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ._types import StrField


class MaskedSpanSchema(BaseModel):
    type: str
    span: tuple[StrField, StrField] = Field(description="문자(코드포인트) 오프셋 — byte 아님 (7.3절)")


class TranscriptSegmentSchema(BaseModel):
    segment_id: str  # 7.3절 계약: 응답에서는 문자열 (DB 는 BIGINT, 경계에서만 변환 — 2026-09-10 조서희 요청)
    speaker: Literal["customer", "agent"]
    text: str = Field(description="마스킹 완료본만 (SEC-1)")
    masked: list[MaskedSpanSchema]
    is_final: StrField
    utterance_end_ms: StrField | None = None


class TranscriptPageResponse(BaseModel):
    call_id: str
    segments: list[TranscriptSegmentSchema]
    total: StrField = Field(description="확정 발화 총수. interim 은 저장되지 않으므로 세어지지 않는다")
    limit: StrField
    offset: StrField
