# Requirement: C-6
"""POST /hub/call-guard-checks — 고객 발화 콜 가드 검사. 스키마 ↔ DTO 변환은 여기서만 한다.

응답에 등급·점수·"안전" 필드를 두지 않는다 (부록 A-1). 화면이 쓸 수 있는 것은 잡힌 표현 목록뿐이다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.call_guard_check_schema import (
    CallGuardCheckRequest,
    CallGuardCheckResponse,
    CallGuardFlagSchema,
)
from hub.app.dtos.call_guard_check_dto import CallGuardCheckCommand
from hub.app.ports.input.call_guard_check_use_case import CallGuardCheckUseCase
from hub.dependencies.call_guard_check_provider import get_call_guard_check_use_case

call_guard_check_router = APIRouter(prefix="/hub", tags=["hub"])


@call_guard_check_router.post("/call-guard-checks", response_model=CallGuardCheckResponse)
async def check_call_guard(
    body: CallGuardCheckRequest,
    use_case: CallGuardCheckUseCase = Depends(get_call_guard_check_use_case),
) -> CallGuardCheckResponse:
    try:
        result = await use_case.check(
            CallGuardCheckCommand(
                call_id=body.call_id,
                segment_id=body.segment_id,
                customer_utterance=body.customer_utterance,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return CallGuardCheckResponse(
        call_id=result.call_id,
        segment_id=result.segment_id,
        flags=[
            CallGuardFlagSchema(
                category=f.category,
                phrase=f.phrase,
                span=list(f.span) if f.span is not None else [],
                source_doc_id=f.source_doc_id,
            )
            for f in result.flags
        ],
    )
