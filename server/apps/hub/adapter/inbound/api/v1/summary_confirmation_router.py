# Requirement: D-1, D-2, D-3
"""POST /hub/calls/{call_id}/summary-confirmation — 상담원이 통화 후 요약 초안을 고쳐서 확정한다.

**상담원 토큰이 필요하다**(`decisions/307`) — 확정은 사람이 했다는 표시라 익명으로 받지 않는다. 누가 했는지는 저장하지 않는다.
이미 확정된 통화 409 · 없는 통화 404 · DB 없음 501. 확정 뒤 `POST …/close` 로 초안을 다시 만들면 409 다(덮지 않는다).
"""

from __future__ import annotations

from agent_auth.adapter.inbound.api.agent_guard import require_agent
from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.summary_confirmation_schema import SummaryConfirmationRequest, SummaryConfirmedResponse
from hub.app.dtos.summary_confirmation_dto import SummaryConfirmationCommand
from hub.app.ports.input.summary_confirmation_use_case import SummaryConfirmationUseCase
from hub.app.ports.output.postcall_record_port import SummaryAlreadyConfirmedError
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.summary_confirmation_provider import get_summary_confirmation_use_case

summary_confirmation_router = APIRouter(prefix="/hub", tags=["hub"])


@summary_confirmation_router.post(
    "/calls/{call_id}/summary-confirmation", response_model=SummaryConfirmedResponse,
    dependencies=[Depends(require_agent)],
)
async def confirm_summary(
    call_id: str,
    body: SummaryConfirmationRequest,
    use_case: SummaryConfirmationUseCase = Depends(get_summary_confirmation_use_case),
) -> SummaryConfirmedResponse:
    try:
        confirmed = await use_case.confirm(SummaryConfirmationCommand(
            call_id=call_id, summary_text=body.summary_text, inquiry_type=body.inquiry_type,
            follow_up_actions=tuple(body.follow_up_actions)))
    except CallNotStartedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"통화가 없습니다: {call_id}") from exc
    except SummaryAlreadyConfirmedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 확정된 요약입니다") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return SummaryConfirmedResponse(
        call_id=confirmed.call_id, summary_text=confirmed.summary_text, inquiry_type=confirmed.inquiry_type,
        follow_up_actions=list(confirmed.follow_up_actions), confirmed=True, confirmed_at=confirmed.confirmed_at.isoformat())
