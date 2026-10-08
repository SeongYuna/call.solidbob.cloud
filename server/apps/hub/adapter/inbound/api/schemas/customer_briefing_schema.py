# Requirement: F-3
"""HTTP 표면 스키마 — 통화 수신 전 고객 브리핑. 값은 전부 문자열(`_types.StrField`, 7.3절 규칙). **고객 식별 정보 필드가 없다.**"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField


class BriefingPurposeSchema(BaseModel):
    category: str = Field(description="재문의 | 후속 확인 | 서류 보완 | 컴플레인 | 신규 문의 — **추정**이다")
    text: str
    source: str = Field(description="model | rule")


class BriefingEvidenceSchema(BaseModel):
    call_id: str
    started_at: str
    inquiry_type: str | None = None
    summary_confirmed: StrField
    incomplete_procedures: list[str]


class BriefingSignalsSchema(BaseModel):
    open_follow_ups: StrField
    call_guard_categories: list[str]
    blacklisted: StrField


class CustomerBriefingResponse(BaseModel):
    call_id: str
    status: str = Field(description="ready | first_contact | unidentified")
    prior_call_count: StrField
    purpose: BriefingPurposeSchema | None = None
    briefing_lines: list[str]
    evidence: list[BriefingEvidenceSchema]
    signals: BriefingSignalsSchema
    generated_at: str
