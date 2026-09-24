# Requirement: J-4
"""만료 변경 이력을 읽는 두 문 — 둘 다 관리자 로그인이 필요하다.

- `GET /hub/blacklist-entries/{entry_id}/expiry-changes` — 등록 1건의 이력(오래된 순).
- `GET /hub/blacklist-expiry-changes` — 등록을 가리지 않는 최근 변경(최근 순). **감사 로그가 읽는다**
  (수동 QA Q-67 — 만료일 변경이 관리자 행위인데 감사 로그에 안 남았다. 등록마다 위 문을 부르면 N+1 이다).
"""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from fastapi import APIRouter, Depends, HTTPException, Query, status

from hub.adapter.inbound.api.schemas.blacklist_expiry_change_schema import (
    ExpiryChangeItemSchema,
    ExpiryChangeListResponse,
    RecentExpiryChangeListResponse,
)
from hub.app.ports.input.blacklist_expiry_change_list_use_case import BlacklistExpiryChangeListUseCase
from hub.app.ports.input.blacklist_expiry_change_recent_use_case import BlacklistRecentExpiryChangeUseCase
from hub.app.ports.output.blacklist_port import BlacklistNotFound
from hub.dependencies.blacklist_expiry_change_provider import (
    get_blacklist_expiry_change_list_use_case,
    get_blacklist_recent_expiry_change_use_case,
)

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


@blacklist_expiry_change_list_router.get(
    "/blacklist-expiry-changes", response_model=RecentExpiryChangeListResponse,
    dependencies=[Depends(require_admin)],
)
async def list_recent_blacklist_expiry_changes(
    limit: int = Query(50, ge=1, le=200, description="최근 몇 건까지"),
    use_case: BlacklistRecentExpiryChangeUseCase = Depends(get_blacklist_recent_expiry_change_use_case),
) -> RecentExpiryChangeListResponse:
    changes = await use_case.recent(limit)
    return RecentExpiryChangeListResponse(changes=[ExpiryChangeItemSchema.from_dto(c) for c in changes])
