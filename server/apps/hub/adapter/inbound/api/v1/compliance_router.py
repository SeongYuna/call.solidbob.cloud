# Requirement: C-1, C-2, C-3, C-4
"""POST /hub/compliance-checks — 상담원 발화 검사. 스키마 ↔ DTO 변환은 여기서만 한다.

응답에 등급·점수·"안전" 필드를 두지 않는다 (부록 A-1). 화면이 쓸 수 있는 것은 잡힌 표현 목록뿐이다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.compliance_schema import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceFindingSchema,
)
from hub.adapter.inbound.api.schemas.recommendation_schema import SourceSchema
from hub.app.dtos.compliance_dto import ComplianceCheckCommand
from hub.app.ports.input.compliance_check_use_case import ComplianceCheckUseCase
from hub.dependencies.compliance_provider import get_compliance_check_use_case

compliance_router = APIRouter(prefix="/hub", tags=["hub"])


@compliance_router.post("/compliance-checks", response_model=ComplianceCheckResponse)
async def check_compliance(
    body: ComplianceCheckRequest,
    use_case: ComplianceCheckUseCase = Depends(get_compliance_check_use_case),
) -> ComplianceCheckResponse:
    try:
        result = await use_case.check(
            ComplianceCheckCommand(
                call_id=body.call_id,
                segment_id=body.segment_id,
                agent_utterance=body.agent_utterance,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return ComplianceCheckResponse(
        call_id=result.call_id,
        segment_id=str(result.segment_id),
        findings=[
            ComplianceFindingSchema(
                rule_code=f.rule_code,
                phrase=f.phrase,
                alternative_source=(
                    SourceSchema(doc_id=f.alternative_source.doc_id, title=f.alternative_source.title)
                    if f.alternative_source
                    else None
                ),
            )
            for f in result.findings
        ],
    )
