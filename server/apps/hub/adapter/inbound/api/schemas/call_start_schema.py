# Requirement: 7.3절 전사 이벤트
"""HTTP 표면 스키마 — 통화 시작. 필드명은 db/schema.sql `call` 컬럼과 같다."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ._types import StrField

from hub.app.dtos.call_start_dto import CallDomain


class CallStartRequest(BaseModel):
    call_id: str = Field(min_length=1, max_length=40, description="게이트웨이가 정한 통화 식별자")
    domain: CallDomain = "dasan"
    stt_engine: str = Field(default="google-stt", min_length=1, max_length=30,
                            description="전사 엔진. 가짜 게이트웨이면 'mock' 처럼 사실대로 적는다")
    channel_count: int = Field(default=1, ge=1, le=2, description="V1 실측: 전부 1(모노)")
    started_at: datetime | None = Field(default=None, description="없으면 서버가 받은 시각")
    caller_phone: str | None = Field(
        default=None, max_length=32,
        description="발신 번호(선택). 서버가 곧바로 HMAC 으로 바꿔 고객을 잇고 **평문은 저장·응답하지 않는다**(decisions/304)",
    )


class CallStartedSchema(BaseModel):
    call_id: str
    domain: CallDomain
    stt_engine: str
    channel_count: StrField
    started_at: datetime
    status: str
    created: StrField = Field(description="false 면 이미 있던 통화 — 그대로 두었다")
    customer_linked: StrField = Field(
        description="고객 식별자를 붙였는가. 번호가 없거나 서버에 HMAC 키가 없으면 false. 식별자 값은 싣지 않는다"
    )
