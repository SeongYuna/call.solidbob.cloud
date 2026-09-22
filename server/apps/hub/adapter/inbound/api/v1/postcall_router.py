# Requirement: D-1, D-2, D-3
"""POST /hub/calls/{call_id}/close — 통화 종료 후 요약·유형 제안·후속조치.

응답은 언제나 초안이다. `confirmed` 를 서버가 true 로 만드는 경로는 없다 — 확정은 상담원 몫이다.
초안은 저장된다(`call.summary_text`·`inquiry_type`·`follow_up_action`). 통화가 없으면 404, 이미 확정된 요약이면 409 — 덮지 않는다.
상담원 토큰 또는 서비스 토큰이 없으면 401(`decisions/315`, `hub/dependencies/close_guard.py`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.postcall_schema import (
    CallSummaryResponse,
    FollowUpActionSchema,
    PostcallRequest,
)
from hub.app.dtos.postcall_dto import PostcallCommand
from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.input.postcall_use_case import PostcallUseCase
from hub.app.ports.output.postcall_record_port import SummaryAlreadyConfirmedError
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.close_guard import require_close_caller
from hub.dependencies.postcall_provider import get_postcall_use_case

postcall_router = APIRouter(prefix="/hub", tags=["hub"])


@postcall_router.post(
    "/calls/{call_id}/close",
    response_model=CallSummaryResponse,
    dependencies=[Depends(require_close_caller)],  # 상담원 토큰 또는 서비스 토큰(`decisions/315`)
)
async def close_call(
    call_id: str,
    body: PostcallRequest,
    use_case: PostcallUseCase = Depends(get_postcall_use_case),
) -> CallSummaryResponse:
    if call_id != body.call_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="경로의 call_id 와 본문의 call_id 가 다릅니다",
        )

    try:
        draft = await use_case.close(
            PostcallCommand(
                call_id=call_id,
                segments=tuple(
                    TranscriptEvent(
                        call_id=call_id,
                        segment_id=s.segment_id,
                        speaker=s.speaker,
                        text=s.text,
                        is_final=s.is_final,
                        utterance_end_ms=s.utterance_end_ms,
                    )
                    for s in body.segments
                ),
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except CallNotStartedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"통화가 없습니다: {call_id} — POST /hub/calls 가 먼저 와야 한다") from exc
    except SummaryAlreadyConfirmedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="상담원이 이미 확정한 요약입니다 — 초안으로 덮지 않습니다") from exc

    return CallSummaryResponse(
        call_id=draft.call_id,
        summary_text=draft.summary_text,
        inquiry_type=draft.inquiry_type,
        follow_up_actions=[FollowUpActionSchema(action_text=a.action_text) for a in draft.follow_up_actions],
        confirmed=draft.confirmed,
    )
