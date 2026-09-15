# Requirement: J-1
from __future__ import annotations

from abc import ABC, abstractmethod

from agent_auth.app.dtos.agent_token_dto import AgentTokenItem


class RevokeAgentTokenUseCase(ABC):
    """토큰 폐기. 멱등이다 — 이미 폐기된 것을 다시 폐기해도 에러가 아니다. 없는 id 면 `AgentTokenNotFound`."""

    @abstractmethod
    async def revoke(self, token_id: int) -> AgentTokenItem: ...
