# Requirement: D-1, D-2
"""GET /hub/calls — 지난 통화 목록(최근 시작순). 자막은 `GET /hub/calls/{call_id}/transcript` 로 따로 본다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hub.adapter.inbound.api.schemas.call_list_schema import CallListItemSchema, CallListResponse
from hub.app.dtos.call_list_dto import DEFAULT_LIMIT, MAX_LIMIT, CallListQuery
from hub.app.ports.input.call_list_use_case import CallListUseCase
from hub.dependencies.call_list_provider import get_call_list_use_case

call_list_router = APIRouter(prefix="/hub", tags=["hub"])


@call_list_router.get("/calls", response_model=CallListResponse)
async def list_calls(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    customer_id: str | None = Query(default=None, max_length=64),  # HMAC hex 64자 (decisions/304)
    use_case: CallListUseCase = Depends(get_call_list_use_case),
) -> CallListResponse:
    try:
        page = await use_case.list(CallListQuery(limit=limit, offset=offset, customer_id=customer_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return CallListResponse(
        calls=[
            CallListItemSchema(
                call_id=c.call_id,
                domain=c.domain,
                started_at=c.started_at.isoformat(),
                ended_at=c.ended_at.isoformat() if c.ended_at is not None else None,
                status=c.status,
                stt_engine=c.stt_engine,
                channel_count=c.channel_count,
                customer_id=c.customer_id,
                inquiry_type=c.inquiry_type,
                summary_confirmed=c.summary_confirmed,
            )
            for c in page.calls
        ],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
