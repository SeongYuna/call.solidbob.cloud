# Requirement: J-1
"""`agent_id`(토큰에서 이미 검증됨)로 이름을 찾아온다. `agent` 행이 지워졌을 드문 경우에도
로그인 자체는 막지 않는다 — agent_id 를 이름 대신 돌려준다."""

from __future__ import annotations

from agent_auth.app.dtos.agent_directory_dto import AgentSummary
from agent_auth.app.ports.input.agent_profile_use_case import AgentProfileUseCase
from agent_auth.app.ports.output.agent_directory_port import AgentDirectoryPort


class AgentProfileInteractor(AgentProfileUseCase):
    def __init__(self, agents: AgentDirectoryPort) -> None:
        self._agents = agents

    async def get(self, agent_id: str) -> AgentSummary:
        found = await self._agents.get(agent_id)
        return found if found is not None else AgentSummary(agent_id=agent_id, display_name=agent_id)
