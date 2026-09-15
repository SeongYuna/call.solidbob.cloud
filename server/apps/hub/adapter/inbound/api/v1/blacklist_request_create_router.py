# Requirement: J-1, J-2
"""POST /hub/blacklist-requests — 상담원의 전환 요청. 결정은 관리자 몫이라 여기는 `pending` 만 만든다.

**상담원 토큰이 필요하다**(`decisions/307`). 요청자(`requested_by`)는 본문이 아니라 토큰에서 온다 —
본문으로 받던 때는 `agent` 에 있는 아무 ID 로나 요청할 수 있었다."""

from __future__ import annotations

from agent_auth.adapter.inbound.api.agent_guard import require_agent
from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.blacklist_request_create_schema import (
    BlacklistRequestCreatedResponse,
    BlacklistRequestCreateRequest,
    BlacklistRequestItemSchema,
)
from hub.app.dtos.blacklist_request_create_dto import BlacklistRequestCreateCommand
from hub.app.ports.input.blacklist_request_create_use_case import BlacklistRequestCreateUseCase
from hub.app.ports.output.blacklist_port import BlacklistConflict, BlacklistNotFound, UnknownAgent
from hub.dependencies.blacklist_request_create_provider import get_blacklist_request_create_use_case

blacklist_request_create_router = APIRouter(prefix="/hub", tags=["hub"])


@blacklist_request_create_router.post(
    "/blacklist-requests", response_model=BlacklistRequestCreatedResponse, status_code=status.HTTP_201_CREATED
)
async def create_blacklist_request(
    body: BlacklistRequestCreateRequest,
    agent_id: str = Depends(require_agent),
    use_case: BlacklistRequestCreateUseCase = Depends(get_blacklist_request_create_use_case),
) -> BlacklistRequestCreatedResponse:
    try:
        created = await use_case.create(
            BlacklistRequestCreateCommand(call_id=body.call_id, requested_by=agent_id, reason=body.reason)
        )
    except BlacklistNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BlacklistConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (UnknownAgent, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return BlacklistRequestCreatedResponse(
        request=BlacklistRequestItemSchema.from_dto(created.request), has_distress=created.has_distress
    )
