# Requirement: J-1
"""GET /hub/agents/me — 지금 가진 상담원 토큰이 유효한지 확인하고, 화면에 띄울 이름을 준다.

토큰 유효성 판정은 여기서 하지 않는다 — `require_agent`(→ `CurrentAgentUseCase`)가 이미
401(없음·폐기)·501(PostgreSQL 미설정)을 가려낸다. 여기는 통과한 `agent_id`로 `agent.display_name`을
찾아 붙일 뿐이다 — 대기화면 인사말이 `agent_id`가 아니라 상담원 이름으로 뜬다(사용자 지적,
2026-09-21)."""

from __future__ import annotations

from agent_auth.adapter.inbound.api.agent_guard import require_agent
from fastapi import APIRouter, Depends

from agent_auth.adapter.inbound.api.schemas.agent_me_schema import AgentMeResponse
from agent_auth.app.ports.input.agent_profile_use_case import AgentProfileUseCase
from agent_auth.dependencies.use_case_providers import get_agent_profile_use_case

agent_me_router = APIRouter(prefix="/hub", tags=["agent_auth"])


@agent_me_router.get("/agents/me", response_model=AgentMeResponse)
async def get_agent_me(
    agent_id: str = Depends(require_agent),
    use_case: AgentProfileUseCase = Depends(get_agent_profile_use_case),
) -> AgentMeResponse:
    profile = await use_case.get(agent_id)
    return AgentMeResponse(agent_id=profile.agent_id, display_name=profile.display_name)
