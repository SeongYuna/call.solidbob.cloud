# Requirement: A-1, SEC-1
"""GET /hub/calls/{call_id}/transcript — 상담원 자막 되돌아보기."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hub.adapter.inbound.api.schemas.transcript_query_schema import (
    MaskedSpanSchema,
    TranscriptPageResponse,
    TranscriptSegmentSchema,
)
from hub.app.dtos.transcript_query_dto import DEFAULT_LIMIT, MAX_LIMIT, TranscriptQuery
from hub.app.ports.input.transcript_query_use_case import TranscriptQueryUseCase
from hub.dependencies.transcript_query_provider import get_transcript_query_use_case

transcript_query_router = APIRouter(prefix="/hub", tags=["hub"])


@transcript_query_router.get("/calls/{call_id}/transcript", response_model=TranscriptPageResponse)
async def list_transcript(
    call_id: str,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    use_case: TranscriptQueryUseCase = Depends(get_transcript_query_use_case),
) -> TranscriptPageResponse:
    try:
        page = await use_case.list(TranscriptQuery(call_id=call_id, limit=limit, offset=offset))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return TranscriptPageResponse(
        call_id=page.call_id,
        segments=[
            TranscriptSegmentSchema(
                segment_id=str(s.segment_id),
                speaker=s.speaker,
                text=s.text,
                masked=[MaskedSpanSchema(type=m.type, span=m.span) for m in s.masked],
                is_final=s.is_final,
                utterance_end_ms=s.utterance_end_ms,
            )
            for s in page.segments
        ],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
