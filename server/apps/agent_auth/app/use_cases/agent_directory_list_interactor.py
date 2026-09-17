# Requirement: J-1
from __future__ import annotations

from agent_auth.app.dtos.agent_directory_dto import AgentSummary
from agent_auth.app.ports.input.agent_directory_list_use_case import AgentDirectoryListUseCase
from agent_auth.app.ports.output.agent_directory_port import AgentDirectoryPort


class AgentDirectoryListInteractor(AgentDirectoryListUseCase):
    def __init__(self, agents: AgentDirectoryPort) -> None:
        self._agents = agents

    async def list(self) -> list[AgentSummary]:
        return await self._agents.list()
