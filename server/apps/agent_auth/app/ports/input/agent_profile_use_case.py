# Requirement: J-1
from __future__ import annotations

from abc import ABC, abstractmethod

from agent_auth.app.dtos.agent_directory_dto import AgentSummary


class AgentProfileUseCase(ABC):
    """`GET /hub/agents/me` — 지금 토큰의 상담원 이름을 화면에 보여줄 자리."""

    @abstractmethod
    async def get(self, agent_id: str) -> AgentSummary: ...
