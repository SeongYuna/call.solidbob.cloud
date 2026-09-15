# Requirement: D-1, D-2, D-3
"""GET /hub/calls/{call_id}/summary-revisions — 요약 재수정 이력. 상담원 토큰 필수(사유가 담긴다)."""

from __future__ import annotations

from agent_auth.adapter.inbound.api.agent_guard import require_agent
from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.summary_revision_schema import SummaryRevisionItemSchema, SummaryRevisionListResponse
from hub.app.ports.input.summary_revision_list_use_case import SummaryRevisionListUseCase
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.summary_revision_provider import get_summary_revision_list_use_case

summary_revision_list_router = APIRouter(prefix="/hub", tags=["hub"])


@summary_revision_list_router.get(
    "/calls/{call_id}/summary-revisions", response_model=SummaryRevisionListResponse, dependencies=[Depends(require_agent)]
)
async def list_summary_revisions(
    call_id: str,
    use_case: SummaryRevisionListUseCase = Depends(get_summary_revision_list_use_case),
) -> SummaryRevisionListResponse:
    try:
        revisions = await use_case.list(call_id)
    except CallNotStartedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"통화가 없습니다: {call_id}") from exc
    return SummaryRevisionListResponse(revisions=[SummaryRevisionItemSchema.from_dto(r) for r in revisions])
