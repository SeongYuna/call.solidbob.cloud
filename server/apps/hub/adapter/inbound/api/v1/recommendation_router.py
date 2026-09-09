# Requirement: B-0, B-1, B-2, B-3, B-4, B-5, B-6
"""POST /hub/recommendations — 코어 파이프라인. 스키마 ↔ DTO 변환은 여기서만 한다."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from hub.adapter.inbound.api.schemas.recommendation_schema import (
    CardSchema,
    RecommendRequest,
    RecommendResponse,
    SourceSchema,
)
from hub.app.dtos.recommendation_dto import RecommendCommand
from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.input.recommendation_use_case import RecommendationUseCase
from hub.dependencies.recommendation_provider import get_recommendation_use_case

recommendation_router = APIRouter(prefix="/hub", tags=["hub"])


@recommendation_router.post("/recommendations", response_model=RecommendResponse)
async def recommend(
    body: RecommendRequest,
    use_case: RecommendationUseCase = Depends(get_recommendation_use_case),
) -> RecommendResponse:
    result = await use_case.recommend(
        RecommendCommand(
            event=TranscriptEvent(
                call_id=body.call_id,
                segment_id=body.segment_id,
                speaker=body.speaker,
                text=body.text,
                is_final=body.is_final,
                utterance_end_ms=body.utterance_end_ms,
            ),
            top_k=body.top_k,
        )
    )

    if not result.fired or result.cards is None:
        return RecommendResponse(fired=False, domain=result.domain)

    cards = result.cards
    return RecommendResponse(
        fired=True,
        domain=result.domain,
        call_id=cards.call_id,
        trigger_at_ms=cards.trigger_at_ms,
        cards=[
            CardSchema(
                title=c.title,
                summary=c.summary,
                source=SourceSchema(doc_id=c.source.doc_id, title=c.source.title),
                similarity_score=c.similarity_score,
            )
            for c in cards.cards
        ],
        internal_latency_ms=cards.internal_latency_ms,
    )
