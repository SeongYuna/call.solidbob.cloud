# Requirement: D-1, D-2
"""HTTP 표면 스키마. 필드명은 db `call` 과 같고, 값은 전부 문자열이다(`_types.StrField`)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField


class CallListItemSchema(BaseModel):
    call_id: str
    domain: str
    started_at: str = Field(description="ISO 8601 (UTC 오프셋 포함)")
    ended_at: str | None = None
    status: str
    stt_engine: str = Field(description="`+diarize` 가 붙으면 화자가 추측이다(decisions/303)")
    channel_count: StrField
    customer_id: str | None = Field(default=None, description="발신 번호의 HMAC(decisions/304) — 콜 미디에이터가 X-Caller-Phone 을 넘기고 서버에 HMAC 키가 있을 때만 채워진다. 아니면 null")
    inquiry_type: str | None = Field(default=None, description="D-2 — 통화 후 처리 전이면 null")
    summary_confirmed: StrField = Field(description="D-1~D-3 초안을 상담원이 확정했는가. false 면 초안이거나 아직 없다")


class CallListResponse(BaseModel):
    calls: list[CallListItemSchema]
    total: StrField
    limit: StrField
    offset: StrField
