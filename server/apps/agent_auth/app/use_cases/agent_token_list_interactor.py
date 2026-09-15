# Requirement: J-1
from __future__ import annotations

from agent_auth.app.dtos.agent_token_dto import AgentTokenItem
from agent_auth.app.ports.input.agent_token_list_use_case import AgentTokenListUseCase
from agent_auth.app.ports.output.agent_token_port import AgentTokenPort


class AgentTokenListInteractor(AgentTokenListUseCase):
    def __init__(self, tokens: AgentTokenPort) -> None:
        self._tokens = tokens

    async def list(self, agent_id: str | None) -> list[AgentTokenItem]:
        return await self._tokens.list(agent_id.strip() if agent_id and agent_id.strip() else None)
