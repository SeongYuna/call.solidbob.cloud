# Requirement: J-4
"""HTTP 표면 스키마 — 해제. 해제자는 로그인한 관리자에게서 온다."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .blacklist_entry_list_schema import BlacklistEntryItemSchema


class BlacklistReleaseRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000, description="왜 풀었는가(필수). 저장 전 마스킹, 500자")


class BlacklistReleaseResponse(BaseModel):
    entry: BlacklistEntryItemSchema
