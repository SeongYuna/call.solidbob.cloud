# Requirement: J-4
"""GET /hub/blacklist-entries — 관리자 블랙리스트 관리창. 관리자 로그인이 필요하다."""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from fastapi import APIRouter, Depends, Query

from hub.adapter.inbound.api.schemas.blacklist_entry_list_schema import BlacklistEntryItemSchema, BlacklistEntryListResponse
from hub.app.dtos.blacklist_entry_list_dto import BlacklistEntryListQuery
from hub.app.ports.input.blacklist_entry_list_use_case import BlacklistEntryListUseCase
from hub.dependencies.blacklist_entry_list_provider import get_blacklist_entry_list_use_case

blacklist_entry_list_router = APIRouter(prefix="/hub", tags=["hub"])


@blacklist_entry_list_router.get(
    "/blacklist-entries", response_model=BlacklistEntryListResponse, dependencies=[Depends(require_admin)]
)
async def list_blacklist_entries(
    active_only: bool = Query(default=False),
    use_case: BlacklistEntryListUseCase = Depends(get_blacklist_entry_list_use_case),
) -> BlacklistEntryListResponse:
    entries = await use_case.list(BlacklistEntryListQuery(active_only=active_only))
    return BlacklistEntryListResponse(entries=[BlacklistEntryItemSchema.from_dto(e) for e in entries])
