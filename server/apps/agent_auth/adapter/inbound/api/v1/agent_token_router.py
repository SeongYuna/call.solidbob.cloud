# Requirement: J-1
"""POST /admin/agent-tokens · GET /admin/agent-tokens · POST /admin/agent-tokens/{id}/revoke (`decisions/307`).

**전부 관리자 로그인이 필요하다.** 상담원 로그인 화면은 없다 — 관리자가 토큰을 발급해 상담원에게 건넨다.
토큰 원문은 발급 응답에 한 번만 실린다. 잃어버리면 폐기하고 새로 발급한다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from agent_auth.adapter.inbound.api.schemas.agent_token_schema import (
    AgentTokenItemSchema,
    AgentTokenListResponse,
    IssueAgentTokenRequest,
    IssuedAgentTokenResponse,
)
from agent_auth.app.dtos.agent_token_dto import AgentTokenNotFound, IssueAgentTokenCommand, UnknownAgentError
from agent_auth.app.ports.input.agent_token_list_use_case import AgentTokenListUseCase
from agent_auth.app.ports.input.issue_agent_token_use_case import IssueAgentTokenUseCase
from agent_auth.app.ports.input.revoke_agent_token_use_case import RevokeAgentTokenUseCase
from agent_auth.dependencies.use_case_providers import (
    get_agent_token_list_use_case,
    get_issue_agent_token_use_case,
    get_revoke_agent_token_use_case,
)

agent_token_router = APIRouter(prefix="/admin/agent-tokens", tags=["agent_auth"])


@agent_token_router.post("", response_model=IssuedAgentTokenResponse, status_code=status.HTTP_201_CREATED)
async def issue_agent_token(
    body: IssueAgentTokenRequest,
    admin: AdminAccount = Depends(require_admin),
    use_case: IssueAgentTokenUseCase = Depends(get_issue_agent_token_use_case),
) -> IssuedAgentTokenResponse:
    try:
        issued = await use_case.issue(IssueAgentTokenCommand(agent_id=body.agent_id, issued_by=admin.id))
    except UnknownAgentError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return IssuedAgentTokenResponse(token=issued.token, item=AgentTokenItemSchema.from_dto(issued.item))


@agent_token_router.get("", response_model=AgentTokenListResponse, dependencies=[Depends(require_admin)])
async def list_agent_tokens(
    agent_id: str | None = Query(default=None, max_length=20),
    use_case: AgentTokenListUseCase = Depends(get_agent_token_list_use_case),
) -> AgentTokenListResponse:
    return AgentTokenListResponse(tokens=[AgentTokenItemSchema.from_dto(t) for t in await use_case.list(agent_id)])


@agent_token_router.post(
    "/{token_id}/revoke", response_model=AgentTokenItemSchema, dependencies=[Depends(require_admin)]
)
async def revoke_agent_token(
    token_id: int,
    use_case: RevokeAgentTokenUseCase = Depends(get_revoke_agent_token_use_case),
) -> AgentTokenItemSchema:
    try:
        item = await use_case.revoke(token_id)
    except AgentTokenNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AgentTokenItemSchema.from_dto(item)
