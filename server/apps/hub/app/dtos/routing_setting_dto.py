# Requirement: J-5
"""J-5 베테랑 배정 기준 설정 — 나르기만 한다(`decisions/313`). 기본값은 블랙리스트 도메인이 갖는다(`routing.DEFAULT_VETERAN_YEARS`)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

MIN_VETERAN_YEARS = 0.5  # 0 이면 모두가 베테랑이라 필터가 의미를 잃는다
MAX_VETERAN_YEARS = 40.0


@dataclass(frozen=True)
class RoutingSetting:
    veteran_years: float
    saved: bool  # False 면 저장값이 없어 기본값이다
    updated_at: datetime | None = None
    updated_by: int | None = None  # admin_account.id


@dataclass(frozen=True)
class RoutingSettingCommand:
    veteran_years: float
    updated_by: int
