# Requirement: J-1
"""GET /hub/agents/me — 지금 가진 상담원 토큰이 유효한지 확인한다.

로그인 화면이 토큰을 입력받은 직후 이걸 불러 맞는 토큰인지 본다. 판정은 여기서 하지 않는다 —
`require_agent`(→ `CurrentAgentUseCase`)가 이미 401(없음·폐기)·501(PostgreSQL 미설정)을
가려낸다. 여기는 통과한 `agent_id`를 그대로 돌려줄 뿐이다."""

from __future__ import annotations

from agent_auth.adapter.inbound.api.agent_guard import require_agent
from fastapi import APIRouter, Depends

from agent_auth.adapter.inbound.api.schemas.agent_me_schema import AgentMeResponse

agent_me_router = APIRouter(prefix="/hub", tags=["agent_auth"])


@agent_me_router.get("/agents/me", response_model=AgentMeResponse)
async def get_agent_me(agent_id: str = Depends(require_agent)) -> AgentMeResponse:
    return AgentMeResponse(agent_id=agent_id)
