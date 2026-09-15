# Requirement: J-1, SEC-1
"""토큰을 만들고 **해시만** 저장한 뒤 원문을 한 번 돌려준다. 원문은 이 함수 밖에 남지 않는다."""

from __future__ import annotations

from agent_auth.app.dtos.agent_token_dto import IssueAgentTokenCommand, IssuedAgentToken
from agent_auth.app.ports.input.issue_agent_token_use_case import IssueAgentTokenUseCase
from agent_auth.app.ports.output.agent_token_port import AgentTokenPort
from agent_auth.domain.services.agent_token import hash_token, new_token


class IssueAgentTokenInteractor(IssueAgentTokenUseCase):
    def __init__(self, tokens: AgentTokenPort) -> None:
        self._tokens = tokens

    async def issue(self, command: IssueAgentTokenCommand) -> IssuedAgentToken:
        agent_id = command.agent_id.strip()
        if not agent_id:
            raise ValueError("상담원 ID(agent_id)가 비어 있습니다")
        token = new_token()
        item = await self._tokens.save(agent_id, hash_token(token), command.issued_by)
        return IssuedAgentToken(item=item, token=token)
