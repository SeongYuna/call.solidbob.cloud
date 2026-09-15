# Requirement: J-5
"""HTTP 표면 스키마 — 베테랑 배정 기준. 값은 전부 문자열이다(`_types.StrField`)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField

from hub.app.dtos.routing_setting_dto import MAX_VETERAN_YEARS, MIN_VETERAN_YEARS, RoutingSetting


class RoutingSettingRequest(BaseModel):
    veteran_years: float = Field(ge=MIN_VETERAN_YEARS, le=MAX_VETERAN_YEARS, description="근속 N년 이상이면 베테랑. 근거 있는 값이 아니다 — 조직이 정한다")


class RoutingSettingResponse(BaseModel):
    veteran_years: StrField
    saved: StrField = Field(description="false 면 저장값이 없어 기본값(3년)이다")
    updated_at: str | None = None
    updated_by: StrField | None = Field(default=None, description="admin_account.id")

    @staticmethod
    def from_dto(s: RoutingSetting) -> "RoutingSettingResponse":
        return RoutingSettingResponse(veteran_years=s.veteran_years, saved=s.saved,
                                      updated_at=s.updated_at.isoformat() if s.updated_at else None, updated_by=s.updated_by)
