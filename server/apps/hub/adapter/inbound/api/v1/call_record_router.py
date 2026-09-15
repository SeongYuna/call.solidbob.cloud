# Requirement: B-5, D-1, D-2, D-3, F-2
"""GET /hub/calls/{call_id}/record — 상담기록 재생. 한 통화의 요약 초안·후속조치·추천 카드·필요서류 판정.

전사는 싣지 않는다 — `GET /hub/calls/{call_id}/transcript` 가 페이지로 준다. 감정분석·통번역은 저장되지 않아 없다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.call_record_schema import (
    CallRecordResponse,
    SavedCardSchema,
    SavedClosureItemSchema,
    SavedClosureSchema,
    SavedFollowUpSchema,
    SavedRecommendationSchema,
)
from hub.app.dtos.call_record_dto import CallRecordNotFound
from hub.app.ports.input.call_record_use_case import CallRecordUseCase
from hub.dependencies.call_record_query_provider import get_call_record_use_case

call_record_router = APIRouter(prefix="/hub", tags=["hub"])


@call_record_router.get("/calls/{call_id}/record", response_model=CallRecordResponse)
async def get_call_record(
    call_id: str,
    use_case: CallRecordUseCase = Depends(get_call_record_use_case),
) -> CallRecordResponse:
    try:
        r = await use_case.get(call_id)
    except CallRecordNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return CallRecordResponse(
        call_id=r.call_id,
        status=r.status,
        started_at=r.started_at.isoformat(),
        ended_at=r.ended_at.isoformat() if r.ended_at else None,
        summary_text=r.summary_text,
        inquiry_type=r.inquiry_type,
        summary_confirmed=r.summary_confirmed_at is not None,
        follow_up_actions=[SavedFollowUpSchema(action_text=f.action_text, status=f.status) for f in r.follow_up_actions],
        recommendations=[
            SavedRecommendationSchema(
                recommendation_id=rec.recommendation_id, trigger_at_ms=rec.trigger_at_ms,
                internal_latency_ms=rec.internal_latency_ms, created_at=rec.created_at.isoformat(),
                cards=[SavedCardSchema(card_id=c.card_id, rank=c.rank, title=c.title, summary=c.summary,
                                       source_doc_id=c.source_doc_id, similarity_score=c.similarity_score)
                       for c in rec.cards],
            )
            for rec in r.recommendations
        ],
        closures=[
            SavedClosureSchema(
                closure_id=cl.closure_id, procedure=cl.procedure, verdict=cl.verdict, detected=cl.detected,
                reason=cl.reason, source_doc_id=cl.source_doc_id, decided_at=cl.decided_at.isoformat(),
                items=[SavedClosureItemSchema(rank=i.rank, document_name=i.document_name, informed=i.informed)
                       for i in cl.items],
            )
            for cl in r.closures
        ],
    )
