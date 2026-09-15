# Requirement: J-1
"""요청 토큰 → 상담원 ID. 접두어가 다른 값은 DB 를 보지 않고 거절한다 — 관리자 JWT 를 잘못 실어 보낸 것이다."""

from __future__ import annotations

from agent_auth.app.ports.input.current_agent_use_case import CurrentAgentUseCase
from agent_auth.app.ports.output.agent_token_port import AgentTokenPort
from agent_auth.domain.services.agent_token import hash_token, looks_like_token


class CurrentAgentInteractor(CurrentAgentUseCase):
    def __init__(self, tokens: AgentTokenPort) -> None:
        self._tokens = tokens

    async def current(self, token: str) -> str | None:
        if not looks_like_token(token):
            return None
        return await self._tokens.find_active_agent_id(hash_token(token))
