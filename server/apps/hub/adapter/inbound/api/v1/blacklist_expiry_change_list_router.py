# Requirement: J-4
"""GET /hub/blacklist-entries/{entry_id}/expiry-changes — 만료 변경 이력(관리자 감사 로그). 관리자 로그인이 필요하다."""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.blacklist_expiry_change_schema import ExpiryChangeItemSchema, ExpiryChangeListResponse
from hub.app.ports.input.blacklist_expiry_change_list_use_case import BlacklistExpiryChangeListUseCase
from hub.app.ports.output.blacklist_port import BlacklistNotFound
from hub.dependencies.blacklist_expiry_change_provider import get_blacklist_expiry_change_list_use_case

blacklist_expiry_change_list_router = APIRouter(prefix="/hub", tags=["hub"])


@blacklist_expiry_change_list_router.get(
    "/blacklist-entries/{entry_id}/expiry-changes", response_model=ExpiryChangeListResponse,
    dependencies=[Depends(require_admin)],
)
async def list_blacklist_expiry_changes(
    entry_id: int,
    use_case: BlacklistExpiryChangeListUseCase = Depends(get_blacklist_expiry_change_list_use_case),
) -> ExpiryChangeListResponse:
    try:
        changes = await use_case.list(entry_id)
    except BlacklistNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ExpiryChangeListResponse(changes=[ExpiryChangeItemSchema.from_dto(c) for c in changes])
