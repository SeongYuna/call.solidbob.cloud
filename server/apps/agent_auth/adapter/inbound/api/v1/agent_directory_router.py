# Requirement: J-1
"""GET /admin/agents — 상담원 토큰 발급 화면이 ID 대신 이름으로 고를 수 있게 목록을 준다.
`admin_auth`가 아니라 개발자가 아닌 관리자도 이 화면을 쓴다는 사용자 지적(2026-09-17)에서
나왔다 — 전에는 `agent.agent_id`를 직접 타이핑해야 했다."""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from fastapi import APIRouter, Depends

from agent_auth.adapter.inbound.api.schemas.agent_directory_schema import (
    AgentDirectoryListResponse,
    AgentSummarySchema,
)
from agent_auth.app.ports.input.agent_directory_list_use_case import AgentDirectoryListUseCase
from agent_auth.dependencies.use_case_providers import get_agent_directory_list_use_case

agent_directory_router = APIRouter(prefix="/admin", tags=["agent_auth"], dependencies=[Depends(require_admin)])


@agent_directory_router.get("/agents", response_model=AgentDirectoryListResponse)
async def list_agents(
    use_case: AgentDirectoryListUseCase = Depends(get_agent_directory_list_use_case),
) -> AgentDirectoryListResponse:
    return AgentDirectoryListResponse(agents=[AgentSummarySchema.from_dto(a) for a in await use_case.list()])
