# Requirement: J-4
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlacklistReleaseCommand:
    entry_id: int
    released_by: str  # 로그인한 관리자에 연결된 agent_id (`decisions/304`)
    reason: str  # 왜 풀었는가 — 필수. 저장 전 마스킹
