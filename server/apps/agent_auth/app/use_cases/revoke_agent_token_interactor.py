# Requirement: J-1
"""토큰 폐기 — 행을 지우지 않고 폐기 시각을 남긴다(절대 원칙 8: 누가 언제 쓰던 토큰인지 흔적이 남아야 한다)."""

from __future__ import annotations

from agent_auth.app.dtos.agent_token_dto import AgentTokenItem, AgentTokenNotFound
from agent_auth.app.ports.input.revoke_agent_token_use_case import RevokeAgentTokenUseCase
from agent_auth.app.ports.output.agent_token_port import AgentTokenPort


class RevokeAgentTokenInteractor(RevokeAgentTokenUseCase):
    def __init__(self, tokens: AgentTokenPort) -> None:
        self._tokens = tokens

    async def revoke(self, token_id: int) -> AgentTokenItem:
        item = await self._tokens.revoke(token_id)
        if item is None:
            raise AgentTokenNotFound(f"토큰이 없습니다: {token_id}")
        return item
