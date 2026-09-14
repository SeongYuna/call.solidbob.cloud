# Requirement: C-6
"""HTTP 표면 스키마 — 콜 가드 로그. 필드명은 db `call_guard_flag` 와 같고 값은 전부 문자열이다."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField


class CallGuardFlagItemSchema(BaseModel):
    id: StrField
    call_id: str
    segment_id: StrField
    category: str = Field(description="insult · threat · sexual · distress (DDL CHECK 정본)")
    phrase: str = Field(description="마스킹된 자막에서 잘라낸 표현")
    span: list[StrField]
    source_doc_id: str | None = None
    detected_at: str


class CallGuardFlagListResponse(BaseModel):
    flags: list[CallGuardFlagItemSchema]
    total: StrField
    limit: StrField
    offset: StrField
