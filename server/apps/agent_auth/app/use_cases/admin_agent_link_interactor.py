# Requirement: J-4, 관리자 로그인(구글)
"""관리자 ↔ `agent` 행 연결(`decisions/314`). 판정 없음 — 있으면 그대로, 없으면 붙인다.

`agent_id` 는 `admin-<admin_account.id>` 다. 이름으로 만들지 않는 이유는 `AgentDirectoryPort.ensure_admin` 에 적었다.
"""

from __future__ import annotations

from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.ports.output.admin_account_port import AdminAccountPort
from agent_auth.app.ports.input.admin_agent_link_use_case import AdminAgentLinkUseCase
from agent_auth.app.ports.output.agent_directory_port import AgentDirectoryPort

# `agent.display_name` 이 VARCHAR(30) 이다
_DISPLAY_NAME_MAX = 30


def admin_agent_id(account_id: int) -> str:
    return f"admin-{account_id}"


class AdminAgentLinkInteractor(AdminAgentLinkUseCase):
    def __init__(self, agents: AgentDirectoryPort, admins: AdminAccountPort) -> None:
        self._agents = agents
        self._admins = admins

    async def resolve(self, admin: AdminAccount) -> str:
        if admin.agent_id:
            return admin.agent_id
        agent_id = admin_agent_id(admin.id)
        # 이메일은 이름 자리에 쓰지 않는다 — 구글 프로필 이름이 없으면 ID 를 그대로 보인다
        display_name = (admin.name or agent_id)[:_DISPLAY_NAME_MAX]
        await self._agents.ensure_admin(agent_id, display_name)
        return await self._admins.link_agent(admin.id, agent_id)
