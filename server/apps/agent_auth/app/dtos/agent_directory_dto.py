# Requirement: J-1
"""상담원 목록 DTO — `agent` 테이블에서 토큰 발급 화면이 고를 후보만 나른다."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentSummary:
    agent_id: str
    display_name: str
