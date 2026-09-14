# Requirement: J-4
"""POST /hub/blacklist-entries/{entry_id}/release — 관리자 해제. 행을 지우지 않고 해제 시각·사람·사유를 남긴다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.blacklist_entry_list_schema import BlacklistEntryItemSchema
from hub.adapter.inbound.api.schemas.blacklist_release_schema import BlacklistReleaseRequest, BlacklistReleaseResponse
from hub.app.dtos.blacklist_release_dto import BlacklistReleaseCommand
from hub.app.ports.input.blacklist_release_use_case import BlacklistReleaseUseCase
from hub.app.ports.output.blacklist_port import BlacklistConflict, BlacklistNotFound
from hub.dependencies.blacklist_decider_provider import get_blacklist_decider
from hub.dependencies.blacklist_release_provider import get_blacklist_release_use_case

blacklist_release_router = APIRouter(prefix="/hub", tags=["hub"])


@blacklist_release_router.post("/blacklist-entries/{entry_id}/release", response_model=BlacklistReleaseResponse)
async def release_blacklist_entry(
    entry_id: int,
    body: BlacklistReleaseRequest,
    released_by: str = Depends(get_blacklist_decider),
    use_case: BlacklistReleaseUseCase = Depends(get_blacklist_release_use_case),
) -> BlacklistReleaseResponse:
    try:
        entry = await use_case.release(BlacklistReleaseCommand(entry_id=entry_id, released_by=released_by, reason=body.reason))
    except BlacklistNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BlacklistConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return BlacklistReleaseResponse(entry=BlacklistEntryItemSchema.from_dto(entry))
