# Requirement: J-1, SEC-1
from __future__ import annotations

from abc import ABC, abstractmethod

from agent_auth.app.dtos.agent_token_dto import AgentTokenItem


class AgentTokenPort(ABC):
    """`agent_token` — **해시만 받는다.** 원문 토큰이 이 포트를 넘어가는 메서드가 없다."""

    @abstractmethod
    async def save(self, agent_id: str, token_hash: str, issued_by: int) -> AgentTokenItem:
        """없는 상담원이면 `UnknownAgentError`."""
        ...

    @abstractmethod
    async def find_active_agent_id(self, token_hash: str) -> str | None:
        """폐기되지 않은 토큰의 상담원 ID. 없거나 폐기됐으면 None."""
        ...

    @abstractmethod
    async def list(self, agent_id: str | None) -> list[AgentTokenItem]: ...

    @abstractmethod
    async def revoke(self, token_id: int) -> AgentTokenItem | None:
        """폐기 시각을 남긴다(이미 폐기됐으면 처음 시각을 유지). 없는 id 면 None. 행을 지우지 않는다."""
        ...
