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


class CallStartedSchema(BaseModel):
    call_id: str
    domain: CallDomain
    stt_engine: str
    channel_count: StrField
    started_at: datetime
    status: str
    created: StrField = Field(description="false 면 이미 있던 통화 — 그대로 두었다")
