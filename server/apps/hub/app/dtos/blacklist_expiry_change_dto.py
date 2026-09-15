# Requirement: J-4
from __future__ import annotations

from dataclasses import dataclass

from .blacklist_dto import BlacklistEntry, ExpiryChange


@dataclass(frozen=True)
class BlacklistExpiryChangeCommand:
    """만료를 «지금부터 N일 뒤» 로 다시 정한다 — 연장·단축 모두(`decisions/309`)."""

    entry_id: int
    changed_by: str  # 로그인한 관리자에 연결된 agent_id (`decisions/304`)
    expires_in_days: int  # 1~365 (`blacklist_decision_dto.MAX_EXPIRES_IN_DAYS` — 승인과 같은 상한)
    reason: str  # 필수. 저장 전 마스킹


@dataclass(frozen=True)
class BlacklistExpiryChanged:
    entry: BlacklistEntry
    change: ExpiryChange
