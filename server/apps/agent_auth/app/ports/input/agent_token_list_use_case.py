# Requirement: J-1
from __future__ import annotations

from abc import ABC, abstractmethod

from agent_auth.app.dtos.agent_token_dto import AgentTokenItem


class AgentTokenListUseCase(ABC):
    """발급된 토큰 목록(폐기 포함). 토큰 원문·해시는 담기지 않는다."""

    @abstractmethod
    async def list(self, agent_id: str | None) -> list[AgentTokenItem]: ...
