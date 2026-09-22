# Requirement: F-2
"""POST /hub/closure-checks — 필요서류 체크리스트(호출자가 채운 체크리스트). 스키마 ↔ DTO 변환은 여기서만 한다.

규칙표에 없는 절차는 422 다. 판정할 규칙이 없는 것을 complete 로도 incomplete 로도 돌려주지 않는다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.closure_schema import ClosureCheckRequest, ClosureVerdictResponse
from hub.app.dtos.closure_dto import ClosureCheckCommand
from hub.app.ports.input.closure_check_use_case import ClosureCheckUseCase
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.closure_provider import get_closure_check_use_case

closure_router = APIRouter(prefix="/hub", tags=["hub"])


@closure_router.post("/closure-checks", response_model=ClosureVerdictResponse)
async def check_closure(
    body: ClosureCheckRequest,
    use_case: ClosureCheckUseCase = Depends(get_closure_check_use_case),
) -> ClosureVerdictResponse:
    try:
        verdict = await use_case.check(
            ClosureCheckCommand(call_id=body.call_id, procedure=body.procedure, evidence=body.evidence, reason=body.reason)
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except CallNotStartedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"통화가 없습니다: {body.call_id} — POST /hub/calls 가 먼저 와야 한다",
        ) from exc
    return ClosureVerdictResponse.from_dto(verdict)
