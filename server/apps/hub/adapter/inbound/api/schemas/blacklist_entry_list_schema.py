# Requirement: J-4
"""HTTP 표면 스키마 — 등록 에피소드. 필드명은 db `blacklist_entry` · 프론트 `BlacklistEntryItem` 과 같다."""

from __future__ import annotations

from pydantic import BaseModel, Field

from hub.app.dtos.blacklist_dto import BlacklistEntry


class BlacklistEntryItemSchema(BaseModel):
    entry_id: str
    customer_ref: str = Field(description="발신 번호의 HMAC — 평문이 아니다")
    request_id: str
    approved_at: str
    expires_at: str
    released_at: str | None = None
    released_by: str | None = None
    release_reason: str | None = None
    note: str | None = None

    @staticmethod
    def from_dto(e: BlacklistEntry) -> "BlacklistEntryItemSchema":
        iso = lambda v: v.isoformat() if v is not None else None  # noqa: E731
        return BlacklistEntryItemSchema(
            entry_id=str(e.entry_id), customer_ref=e.customer_ref, request_id=e.request_id,
            approved_at=iso(e.approved_at) or "", expires_at=iso(e.expires_at) or "",
            released_at=iso(e.released_at), released_by=e.released_by, release_reason=e.release_reason, note=e.note,
        )


class BlacklistEntryListResponse(BaseModel):
    entries: list[BlacklistEntryItemSchema]
