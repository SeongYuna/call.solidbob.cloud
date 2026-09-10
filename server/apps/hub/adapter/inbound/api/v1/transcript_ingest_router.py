# Requirement: 7.3절 전사 이벤트, C-5, SEC-1
"""POST /hub/transcripts — 게이트웨이 → 허브. 스키마 ↔ DTO 변환은 여기서만 한다 (유스케이스는 DTO 만 받는다)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from hub.adapter.inbound.api.schemas.transcript_ingest_schema import (
    MaskedSpanSchema,
    TranscriptEventSchema,
    TranscriptIngestRequest,
)
from hub.app.dtos.transcript_ingest_dto import TranscriptIngestCommand
from hub.app.ports.input.transcript_ingest_use_case import TranscriptIngestUseCase
from hub.dependencies.transcript_ingest_provider import get_transcript_ingest_use_case

transcript_ingest_router = APIRouter(prefix="/hub", tags=["hub"])


@transcript_ingest_router.post("/transcripts", response_model=TranscriptEventSchema)
async def ingest_transcript(
    body: TranscriptIngestRequest,
    use_case: TranscriptIngestUseCase = Depends(get_transcript_ingest_use_case),
) -> TranscriptEventSchema:
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
    return TranscriptEventSchema(
        call_id=event.call_id,
        segment_id=str(event.segment_id),
        speaker=event.speaker,
        text=event.text,
        masked=[MaskedSpanSchema(type=s.type, span=s.span) for s in event.masked],
        is_final=event.is_final,
        utterance_end_ms=event.utterance_end_ms,
    )
