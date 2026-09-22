# Requirement: J-4
from __future__ import annotations

from dataclasses import dataclass

MAX_EXPIRES_IN_DAYS = 365  # 만료 없는 영구 표시를 막는 상한(`decisions/205` ⑤). 기본값은 두지 않는다 — 관리자가 정한다


@dataclass(frozen=True)
class BlacklistDecisionCommand:
    request_id: str
    approve: bool
    decided_by: str  # 로그인한 관리자에 연결된 agent_id (`decisions/304`)
    expires_in_days: int | None = None  # 승인이면 필수(1~365). 반려면 무시한다
    note: str | None = None  # 승인이면 메모(선택), 반려면 사유(필수 — `decisions/316`). 저장 전 마스킹
