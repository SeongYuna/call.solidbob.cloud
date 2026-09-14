# Requirement: C-6
"""GET /hub/call-guard-flags — 관리자 콜 가드 로그. 관리자 로그인이 필요하다 — 잡힌 표현이 고객 발화다."""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from fastapi import APIRouter, Depends, HTTPException, Query, status

from hub.adapter.inbound.api.schemas.call_guard_flag_list_schema import CallGuardFlagItemSchema, CallGuardFlagListResponse
from hub.app.dtos.call_guard_flag_list_dto import DEFAULT_LIMIT, MAX_LIMIT, CallGuardFlagListQuery
from hub.app.ports.input.call_guard_flag_list_use_case import CallGuardFlagListUseCase
from hub.dependencies.call_guard_flag_list_provider import get_call_guard_flag_list_use_case

call_guard_flag_list_router = APIRouter(prefix="/hub", tags=["hub"])


@call_guard_flag_list_router.get(
    "/call-guard-flags", response_model=CallGuardFlagListResponse, dependencies=[Depends(require_admin)]
)
async def list_call_guard_flags(
    call_id: str | None = Query(default=None, max_length=40),
    category: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    use_case: CallGuardFlagListUseCase = Depends(get_call_guard_flag_list_use_case),
) -> CallGuardFlagListResponse:
    try:
        page = await use_case.list(CallGuardFlagListQuery(call_id=call_id, category=category, limit=limit, offset=offset))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return CallGuardFlagListResponse(
        flags=[
            CallGuardFlagItemSchema(
                id=f.id, call_id=f.call_id, segment_id=f.segment_id, category=f.category, phrase=f.phrase,
                span=list(f.span), source_doc_id=f.source_doc_id, detected_at=f.detected_at.isoformat(),
            )
            for f in page.flags
        ],
        total=page.total, limit=page.limit, offset=page.offset,
    )
