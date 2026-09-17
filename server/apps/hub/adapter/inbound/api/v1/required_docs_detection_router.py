# Requirement: F-2
"""POST /hub/required-docs-checks — 상담원 발화로 필요서류 안내 여부를 자동 판정한다. 콜 미디에이터가 부른다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.closure_schema import ClosureVerdictResponse
from hub.adapter.inbound.api.schemas.required_docs_detection_schema import RequiredDocsDetectionRequest
from hub.app.dtos.required_docs_detection_dto import RequiredDocsDetectionCommand
from hub.app.ports.input.required_docs_detection_use_case import RequiredDocsDetectionUseCase
from hub.dependencies.required_docs_detection_provider import get_required_docs_detection_use_case

required_docs_detection_router = APIRouter(prefix="/hub", tags=["hub"])


@required_docs_detection_router.post("/required-docs-checks", response_model=ClosureVerdictResponse)
async def check_required_docs(
    body: RequiredDocsDetectionRequest,
    use_case: RequiredDocsDetectionUseCase = Depends(get_required_docs_detection_use_case),
) -> ClosureVerdictResponse:
    try:
        verdict = await use_case.check(
            RequiredDocsDetectionCommand(
                call_id=body.call_id, procedure=body.procedure, agent_utterances=tuple(body.agent_utterances)
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return ClosureVerdictResponse.from_dto(verdict)
