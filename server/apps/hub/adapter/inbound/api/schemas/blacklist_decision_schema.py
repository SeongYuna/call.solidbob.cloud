# Requirement: J-4
"""HTTP 표면 스키마 — 승인·반려. 결정자는 본문이 아니라 로그인한 관리자에게서 온다."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .blacklist_request_create_schema import BlacklistRequestItemSchema

from hub.app.dtos.blacklist_decision_dto import MAX_EXPIRES_IN_DAYS


class BlacklistDecisionRequest(BaseModel):
    approve: bool
    expires_in_days: int | None = Field(
        default=None, ge=1, le=MAX_EXPIRES_IN_DAYS, description="승인이면 필수. 기본값이 없다 — 관리자가 정한다"
    )
    note: str | None = Field(default=None, max_length=2000, description="승인 메모(선택). 저장 전 마스킹, 500자")


class BlacklistDecisionResponse(BaseModel):
    request: BlacklistRequestItemSchema
