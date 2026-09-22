# Requirement: J-5
"""PUT /admin/agents/{agent_id}/hired-on — 관리자가 상담원 입사일을 넣는다(`decisions/321`).

J-5 베테랑 판정은 `agent.hired_on` 으로 근속을 센다(`decisions/204`·`313`). 그런데 상담원 행은 토큰 발급 때
이름만으로 만들어지고 입사일을 넣는 길이 없어서, 운영의 모든 상담원이 근속 0년 — **베테랑이 나올 수 없었다.**
없는 상담원·관리자 행 404 · 오늘보다 뒤 422 · 관리자 로그인 없음 401 · DB 없음 501.
"""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from fastapi import APIRouter, Depends, HTTPException, status

from agent_auth.adapter.inbound.api.schemas.agent_directory_schema import AgentHiredOnRequest, AgentSummarySchema
from agent_auth.app.dtos.agent_directory_dto import AgentHiredOnCommand
from agent_auth.app.ports.input.agent_hired_on_use_case import AgentHiredOnUseCase
from agent_auth.dependencies.use_case_providers import get_agent_hired_on_use_case

agent_hired_on_router = APIRouter(prefix="/admin", tags=["agent_auth"], dependencies=[Depends(require_admin)])


@agent_hired_on_router.put("/agents/{agent_id}/hired-on", response_model=AgentSummarySchema)
async def set_hired_on(
    agent_id: str,
    body: AgentHiredOnRequest,
    use_case: AgentHiredOnUseCase = Depends(get_agent_hired_on_use_case),
) -> AgentSummarySchema:
    try:
        saved = await use_case.set(AgentHiredOnCommand(agent_id=agent_id, hired_on=body.hired_on))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"상담원이 없습니다: {agent_id}")
    return AgentSummarySchema.from_dto(saved)
