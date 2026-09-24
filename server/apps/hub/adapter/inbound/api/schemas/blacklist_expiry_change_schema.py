# Requirement: J-4
"""HTTP 표면 스키마 — 블랙리스트 등록 만료 변경(연장·단축)과 그 이력. 값은 전부 문자열이다(`_types.StrField`)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField
from .blacklist_entry_list_schema import BlacklistEntryItemSchema

from hub.app.dtos.blacklist_decision_dto import MAX_EXPIRES_IN_DAYS
from hub.app.dtos.blacklist_dto import ExpiryChange


class BlacklistExpiryChangeRequest(BaseModel):
    expires_in_days: int = Field(ge=1, le=MAX_EXPIRES_IN_DAYS, description="지금부터 N일 뒤로 다시 정한다 — 연장·단축 모두. 기본값 없음")
    reason: str = Field(min_length=1, max_length=2000, description="왜 바꾸는가(필수). 저장 전 마스킹, 500자")


class ExpiryChangeItemSchema(BaseModel):
    change_id: StrField
    entry_id: StrField
    previous_expires_at: str
    new_expires_at: str
    changed_by: str
    reason: str = Field(description="마스킹된 사유")
    changed_at: str

    @staticmethod
    def from_dto(c: ExpiryChange) -> "ExpiryChangeItemSchema":
        return ExpiryChangeItemSchema(
            change_id=c.change_id, entry_id=c.entry_id,
            previous_expires_at=c.previous_expires_at.isoformat(), new_expires_at=c.new_expires_at.isoformat(),
            changed_by=c.changed_by, reason=c.reason, changed_at=c.changed_at.isoformat() if c.changed_at else "",
        )


class BlacklistExpiryChangeResponse(BaseModel):
    entry: BlacklistEntryItemSchema
    change: ExpiryChangeItemSchema


class ExpiryChangeListResponse(BaseModel):
    changes: list[ExpiryChangeItemSchema] = Field(description="오래된 순")


class RecentExpiryChangeListResponse(BaseModel):
    """관리자 감사 로그가 읽는다 — 등록을 가리지 않고 **최근 순**이다(등록별 이력과 정렬이 반대)."""

    changes: list[ExpiryChangeItemSchema] = Field(description="최근 순")
