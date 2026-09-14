# Requirement: J-4
"""GET /hub/blacklist-requests — 관리자 승인요청창. **관리자 로그인이 필요하다** — 요청에는 고객 식별자와 자막이 있다."""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from fastapi import APIRouter, Depends, HTTPException, Query, status

from hub.adapter.inbound.api.schemas.blacklist_request_create_schema import BlacklistRequestItemSchema
from hub.adapter.inbound.api.schemas.blacklist_request_list_schema import BlacklistRequestListResponse
from hub.app.dtos.blacklist_request_list_dto import BlacklistRequestListQuery
from hub.app.ports.input.blacklist_request_list_use_case import BlacklistRequestListUseCase
from hub.dependencies.blacklist_request_list_provider import get_blacklist_request_list_use_case

blacklist_request_list_router = APIRouter(prefix="/hub", tags=["hub"])


@blacklist_request_list_router.get(
    "/blacklist-requests", response_model=BlacklistRequestListResponse, dependencies=[Depends(require_admin)]
)
async def list_blacklist_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    use_case: BlacklistRequestListUseCase = Depends(get_blacklist_request_list_use_case),
) -> BlacklistRequestListResponse:
    try:
        requests = await use_case.list(BlacklistRequestListQuery(status=status_filter))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return BlacklistRequestListResponse(requests=[BlacklistRequestItemSchema.from_dto(r) for r in requests])
