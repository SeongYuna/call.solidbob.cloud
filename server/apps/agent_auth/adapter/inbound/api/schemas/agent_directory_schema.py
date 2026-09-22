# Requirement: J-1
"""HTTP 표면 스키마 — 상담원 목록(이름으로 토큰 발급 대상을 고르는 화면용)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agent_auth.app.dtos.agent_directory_dto import AgentSummary


class AgentSummarySchema(BaseModel):
    agent_id: str
    display_name: str
    hired_on: str | None = Field(default=None, description="입사일 YYYY-MM-DD — J-5 근속을 여기서 센다. null 이면 0년(`decisions/321`)")

    @staticmethod
    def from_dto(item: AgentSummary) -> "AgentSummarySchema":
        return AgentSummarySchema(agent_id=item.agent_id, display_name=item.display_name,
                                  hired_on=item.hired_on.isoformat() if item.hired_on else None)


class AgentHiredOnRequest(BaseModel):
    hired_on: date | None = Field(description="YYYY-MM-DD. null 이면 지운다(근속 0년). 오늘보다 뒤는 422")


class AgentDirectoryListResponse(BaseModel):
    agents: list[AgentSummarySchema]
