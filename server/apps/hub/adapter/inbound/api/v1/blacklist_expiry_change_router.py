# Requirement: J-4
"""POST /hub/blacklist-entries/{entry_id}/expiry — 관리자 만료 연장·단축(`decisions/309`, `decisions/205` 「연장은 새 요청으로만」 철회).

만료를 «지금부터 N일 뒤» 로 다시 정하고 변경 1건을 쌓는다. 사유 필수 · 해제된 등록은 409.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.blacklist_entry_list_schema import BlacklistEntryItemSchema
from hub.adapter.inbound.api.schemas.blacklist_expiry_change_schema import (
    BlacklistExpiryChangeRequest,
    BlacklistExpiryChangeResponse,
    ExpiryChangeItemSchema,
)
from hub.app.dtos.blacklist_expiry_change_dto import BlacklistExpiryChangeCommand
from hub.app.ports.input.blacklist_expiry_change_use_case import BlacklistExpiryChangeUseCase
from hub.app.ports.output.blacklist_port import BlacklistConflict, BlacklistNotFound
from hub.dependencies.blacklist_decider_provider import get_blacklist_decider
from hub.dependencies.blacklist_expiry_change_provider import get_blacklist_expiry_change_use_case

blacklist_expiry_change_router = APIRouter(prefix="/hub", tags=["hub"])


@blacklist_expiry_change_router.post(
    "/blacklist-entries/{entry_id}/expiry", response_model=BlacklistExpiryChangeResponse
)
async def change_blacklist_expiry(
    entry_id: int,
    body: BlacklistExpiryChangeRequest,
    changed_by: str = Depends(get_blacklist_decider),
    use_case: BlacklistExpiryChangeUseCase = Depends(get_blacklist_expiry_change_use_case),
) -> BlacklistExpiryChangeResponse:
    try:
        changed = await use_case.change(BlacklistExpiryChangeCommand(
            entry_id=entry_id, changed_by=changed_by, expires_in_days=body.expires_in_days, reason=body.reason))
    except BlacklistNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BlacklistConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return BlacklistExpiryChangeResponse(
        entry=BlacklistEntryItemSchema.from_dto(changed.entry), change=ExpiryChangeItemSchema.from_dto(changed.change))
