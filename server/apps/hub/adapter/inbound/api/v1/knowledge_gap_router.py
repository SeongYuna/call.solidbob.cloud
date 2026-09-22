# Requirement: D-4
"""POST /hub/knowledge-gaps — 「이 답을 못 찾았다」 신고 수집. 상담원 토큰 · 설명은 마스킹 후 저장(`decisions/322`)."""

from __future__ import annotations

from agent_auth.adapter.inbound.api.agent_guard import require_agent
from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.knowledge_gap_schema import (
    KnowledgeGapRequest,
    KnowledgeGapResponse,
)
from hub.app.dtos.knowledge_gap_dto import KnowledgeGapReport
from hub.app.ports.input.knowledge_gap_use_case import KnowledgeGapUseCase
from hub.dependencies.knowledge_gap_provider import get_knowledge_gap_use_case

# 상담원 토큰(`decisions/322`) — 부르는 곳이 아직 없어 이행기 없이 닫는다. 누가 신고했는지는 저장하지 않는다(부록 A-1)
knowledge_gap_router = APIRouter(prefix="/hub", tags=["hub"], dependencies=[Depends(require_agent)])


@knowledge_gap_router.post(
    "/knowledge-gaps", response_model=KnowledgeGapResponse, status_code=status.HTTP_201_CREATED
)
async def report_knowledge_gap(
    body: KnowledgeGapRequest,
    use_case: KnowledgeGapUseCase = Depends(get_knowledge_gap_use_case),
) -> KnowledgeGapResponse:
    try:
        receipt = await use_case.report(
            KnowledgeGapReport(
                module=body.module,
                description=body.description,
                call_id=body.call_id,
                segment_id=body.segment_id,
                closure_id=body.closure_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return KnowledgeGapResponse(gap_id=receipt.gap_id, module=receipt.module)
