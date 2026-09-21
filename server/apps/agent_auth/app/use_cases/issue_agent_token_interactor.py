# Requirement: J-1, SEC-1
"""토큰을 만들고 **해시만** 저장한 뒤 원문을 한 번 돌려준다. 원문은 이 함수 밖에 남지 않는다.

`decisions/406` — 발급 대상은 `agent_id` 또는 이름 어느 쪽으로 와도 된다. 상담원 목록 관리
화면이 없는 테스트 단계라, 없는 이름이면 그 자리에서 새 상담원으로 만든다.
"""

from __future__ import annotations

from agent_auth.app.dtos.agent_token_dto import IssueAgentTokenCommand, IssuedAgentToken
from agent_auth.app.ports.input.issue_agent_token_use_case import IssueAgentTokenUseCase
from agent_auth.app.ports.output.agent_directory_port import AgentDirectoryPort
from agent_auth.app.ports.output.agent_token_port import AgentTokenPort
from agent_auth.domain.services.agent_token import hash_token, new_token


class IssueAgentTokenInteractor(IssueAgentTokenUseCase):
    def __init__(self, tokens: AgentTokenPort, agents: AgentDirectoryPort) -> None:
        self._tokens = tokens
        self._agents = agents

    async def issue(self, command: IssueAgentTokenCommand) -> IssuedAgentToken:
        identifier = command.agent_id.strip()
        if not identifier:
            raise ValueError("상담원 이름 또는 ID가 비어 있습니다")
        agent = await self._agents.resolve_or_create(identifier)
        token = new_token()
        item = await self._tokens.save(agent.agent_id, hash_token(token), command.issued_by)
        return IssuedAgentToken(item=item, token=token)
