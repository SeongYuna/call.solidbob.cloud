# Requirement: 7.3절 전사 이벤트, C-5, SEC-1
"""POST /hub/transcripts — 게이트웨이 → 허브. 스키마 ↔ DTO 변환은 여기서만 한다 (유스케이스는 DTO 만 받는다)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from hub.adapter.inbound.api.schemas.transcript_ingest_schema import (
    MaskedSpanSchema,
    TranscriptEventSchema,
    TranscriptIngestRequest,
)
from hub.app.dtos.transcript_ingest_dto import TranscriptIngestCommand
from hub.app.ports.input.transcript_ingest_use_case import TranscriptIngestUseCase
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.transcript_ingest_provider import get_transcript_ingest_use_case

transcript_ingest_router = APIRouter(prefix="/hub", tags=["hub"])


@transcript_ingest_router.post(
    "/transcripts",
    response_model=TranscriptEventSchema,
    responses={409: {"description": "통화가 시작되지 않았다 — `POST /hub/calls` 를 먼저 보낸다"}},
)
async def ingest_transcript(
    body: TranscriptIngestRequest,
    use_case: TranscriptIngestUseCase = Depends(get_transcript_ingest_use_case),
) -> TranscriptEventSchema:
    try:
        event = await use_case.ingest(
            TranscriptIngestCommand(
                call_id=body.call_id,
                segment_id=body.segment_id,
                speaker=body.speaker,
                raw_text=body.text,
                is_final=body.is_final,
                utterance_end_ms=body.utterance_end_ms,
            )
        )
    except CallNotStartedError as exc:
        # 원문(body.text)은 싣지 않는다 — 409 본문도 응답이다 (SEC-1)
        raise HTTPException(
            status_code=409,
            detail=f"통화 '{exc.call_id}' 가 시작되지 않았다 — POST /hub/calls 를 전사보다 먼저 보낸다 "
                   "(decisions/301)",
        ) from exc
    return TranscriptEventSchema(
        call_id=event.call_id,
        segment_id=str(event.segment_id),
        speaker=event.speaker,
        text=event.text,
        masked=[MaskedSpanSchema(type=s.type, span=s.span) for s in event.masked],
        is_final=event.is_final,
        utterance_end_ms=event.utterance_end_ms,
    )
