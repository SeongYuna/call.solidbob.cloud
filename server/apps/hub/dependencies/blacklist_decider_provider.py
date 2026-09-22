# Requirement: J-4, 관리자 로그인(구글)
"""블랙리스트를 **결정**할 사람 — 관리자 로그인(`require_admin`) + 연결된 상담원 마스터 ID(`decisions/304`).

`blacklist_request.decided_by`·`blacklist_entry.released_by` 가 `agent` 를 참조한다. 전에는 `admin_account.agent_id` 가
비어 있으면 409 였고 운영자가 SQL 로 채워야 했다 — 09-15 첫 로그인부터 운영의 승인·해제가 전부 막혀 있었다.
이제 처음 결정할 때 **그 관리자 전용 `agent` 행(`admin-<id>`, `role='admin'`)을 붙인다**(`decisions/314`).
"""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from agent_auth.app.ports.input.admin_agent_link_use_case import AdminAgentLinkUseCase
from agent_auth.dependencies.use_case_providers import get_admin_agent_link_use_case
from fastapi import Depends


async def get_blacklist_decider(
    admin: AdminAccount = Depends(require_admin),  # ⚠ 순서가 계약이다 — 헤더 없으면 DB 전에 401(`admin_guard`)
    link: AdminAgentLinkUseCase = Depends(get_admin_agent_link_use_case),
) -> str:
    return await link.resolve(admin)
