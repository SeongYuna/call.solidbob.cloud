# Requirement: J-4
"""POST /hub/blacklist-requests/{request_id}/decision — 관리자 승인·반려. 승인이면 등록 에피소드가 생긴다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.blacklist_decision_schema import BlacklistDecisionRequest, BlacklistDecisionResponse
from hub.adapter.inbound.api.schemas.blacklist_request_create_schema import BlacklistRequestItemSchema
from hub.app.dtos.blacklist_decision_dto import BlacklistDecisionCommand
from hub.app.ports.input.blacklist_decision_use_case import BlacklistDecisionUseCase
from hub.app.ports.output.blacklist_port import BlacklistConflict, BlacklistNotFound
from hub.dependencies.blacklist_decider_provider import get_blacklist_decider
from hub.dependencies.blacklist_decision_provider import get_blacklist_decision_use_case

blacklist_decision_router = APIRouter(prefix="/hub", tags=["hub"])


@blacklist_decision_router.post("/blacklist-requests/{request_id}/decision", response_model=BlacklistDecisionResponse)
async def decide_blacklist_request(
    request_id: str,
    body: BlacklistDecisionRequest,
    decided_by: str = Depends(get_blacklist_decider),
    use_case: BlacklistDecisionUseCase = Depends(get_blacklist_decision_use_case),
) -> BlacklistDecisionResponse:
    try:
        decided = await use_case.decide(BlacklistDecisionCommand(
            request_id=request_id, approve=body.approve, decided_by=decided_by,
            expires_in_days=body.expires_in_days, note=body.note,
        ))
    except BlacklistNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BlacklistConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return BlacklistDecisionResponse(request=BlacklistRequestItemSchema.from_dto(decided))
