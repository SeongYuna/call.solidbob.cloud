# Requirement: J-4, 관리자 로그인(구글)
"""블랙리스트를 **결정**할 사람 — 관리자 로그인(`require_admin`) + 연결된 상담원 마스터 ID(`decisions/304`).

`blacklist_request.decided_by`·`blacklist_entry.released_by` 가 `agent` 를 참조한다. 로그인한 관리자에게
`admin_account.agent_id` 가 없으면 **누구로 기록할지 지어내지 않고 409** 로 거절한다.
"""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from fastapi import Depends, HTTPException, status


async def get_blacklist_decider(admin: AdminAccount = Depends(require_admin)) -> str:
    if not admin.agent_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이 관리자 계정에 상담원 마스터(agent_id)가 연결되지 않았습니다 — admin_account.agent_id 를 채워야 합니다",
        )
    return admin.agent_id
