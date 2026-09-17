# Requirement: J-1
"""HTTP 표면 스키마 — 상담원 목록(이름으로 토큰 발급 대상을 고르는 화면용)."""

from __future__ import annotations

from pydantic import BaseModel

from agent_auth.app.dtos.agent_directory_dto import AgentSummary


class AgentSummarySchema(BaseModel):
    agent_id: str
    display_name: str

    @staticmethod
    def from_dto(item: AgentSummary) -> "AgentSummarySchema":
        return AgentSummarySchema(agent_id=item.agent_id, display_name=item.display_name)


class AgentDirectoryListResponse(BaseModel):
    agents: list[AgentSummarySchema]
