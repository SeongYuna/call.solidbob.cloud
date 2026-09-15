# Requirement: J-1
from __future__ import annotations

from abc import ABC, abstractmethod

from agent_auth.app.dtos.agent_token_dto import IssueAgentTokenCommand, IssuedAgentToken


class IssueAgentTokenUseCase(ABC):
    """관리자가 상담원 한 명에게 토큰을 발급한다. 원문은 결과에 한 번만 담긴다."""

    @abstractmethod
    async def issue(self, command: IssueAgentTokenCommand) -> IssuedAgentToken: ...
