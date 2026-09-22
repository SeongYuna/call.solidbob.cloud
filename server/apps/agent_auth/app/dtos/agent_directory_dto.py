# Requirement: J-1
"""상담원 목록 DTO — `agent` 테이블에서 토큰 발급 화면이 고를 후보만 나른다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class AgentSummary:
    agent_id: str
    display_name: str
    hired_on: date | None = None  # J-5 근속을 세는 입사일(`decisions/321`). 없으면 0년으로 센다


@dataclass(frozen=True)
class AgentHiredOnCommand:
    agent_id: str
    hired_on: date | None  # None 이면 지운다
