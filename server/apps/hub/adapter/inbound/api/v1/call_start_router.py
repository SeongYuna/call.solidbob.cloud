# Requirement: 7.3절 전사 이벤트
"""POST /hub/calls — 게이트웨이가 통화 시작을 알린다. 전사(`POST /hub/transcripts`)보다 먼저 와야 한다.

`transcript_segment.call_id → call` 외래키 때문이다. 이 경로가 없어서 전사 저장이 첫 건부터
실패했다(2026-09-10, `_project/decisions/301`). 스키마 ↔ DTO 변환은 여기서만 한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from hub.adapter.inbound.api.schemas.call_start_schema import CallStartedSchema, CallStartRequest
from hub.app.dtos.call_start_dto import CallStartCommand
from hub.app.ports.input.call_start_use_case import CallStartUseCase
from hub.dependencies.call_start_provider import get_call_start_use_case

call_start_router = APIRouter(prefix="/hub", tags=["hub"])


@call_start_router.post("/calls", response_model=CallStartedSchema)
async def start_call(
    body: CallStartRequest,
    use_case: CallStartUseCase = Depends(get_call_start_use_case),
) -> CallStartedSchema:
    call = await use_case.start(
        CallStartCommand(
            call_id=body.call_id,
            domain=body.domain,
            stt_engine=body.stt_engine,
            channel_count=body.channel_count,
            started_at=body.started_at,
        )
    )
    return CallStartedSchema(
        call_id=call.call_id,
        domain=call.domain,
        stt_engine=call.stt_engine,
        channel_count=call.channel_count,
        started_at=call.started_at,
        status=call.status,
        created=call.created,
    )
