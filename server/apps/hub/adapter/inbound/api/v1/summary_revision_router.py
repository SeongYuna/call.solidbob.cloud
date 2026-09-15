# Requirement: D-1, D-2, D-3
"""POST /hub/calls/{call_id}/summary-revision — 확정된 요약을 사유와 함께 고친다(`decisions/311`).

상담원 토큰 필수 · 확정 전이면 409(확정을 먼저) · 없는 통화 404. 고치기 전 값은 이력으로 남고 누가 고쳤는지는 저장하지 않는다.
"""

from __future__ import annotations

from agent_auth.adapter.inbound.api.agent_guard import require_agent
from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.summary_revision_schema import (
    SummaryRevisedResponse,
    SummaryRevisionItemSchema,
    SummaryRevisionRequest,
)
from hub.app.dtos.summary_revision_dto import SummaryRevisionCommand
from hub.app.ports.input.summary_revision_use_case import SummaryRevisionUseCase
from hub.app.ports.output.summary_revision_port import SummaryNotConfirmedError
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.summary_revision_provider import get_summary_revision_use_case

summary_revision_router = APIRouter(prefix="/hub", tags=["hub"])


@summary_revision_router.post(
    "/calls/{call_id}/summary-revision", response_model=SummaryRevisedResponse, dependencies=[Depends(require_agent)]
)
async def revise_summary(
    call_id: str,
    body: SummaryRevisionRequest,
    use_case: SummaryRevisionUseCase = Depends(get_summary_revision_use_case),
) -> SummaryRevisedResponse:
    try:
        revised = await use_case.revise(SummaryRevisionCommand(
            call_id=call_id, summary_text=body.summary_text, reason=body.reason, inquiry_type=body.inquiry_type,
            follow_up_actions=tuple(body.follow_up_actions)))
    except CallNotStartedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"통화가 없습니다: {call_id}") from exc
    except SummaryNotConfirmedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="아직 확정되지 않은 요약입니다 — POST …/summary-confirmation 으로 먼저 확정합니다") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return SummaryRevisedResponse(
        call_id=revised.call_id, summary_text=revised.summary_text, inquiry_type=revised.inquiry_type,
        follow_up_actions=list(revised.follow_up_actions), revision=SummaryRevisionItemSchema.from_dto(revised.revision))
