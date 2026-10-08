# Requirement: F-3
"""GET /hub/calls/{call_id}/briefing — 「통화받기」 전 고객 브리핑(`decisions/220`). 목적은 **추정**이다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.customer_briefing_schema import (
    BriefingEvidenceSchema, BriefingPurposeSchema, BriefingSignalsSchema, CustomerBriefingResponse,
)
from hub.app.dtos.customer_briefing_dto import BriefingCallNotFound
from hub.app.ports.input.customer_briefing_use_case import CustomerBriefingUseCase
from hub.dependencies.customer_briefing_provider import get_customer_briefing_use_case

customer_briefing_router = APIRouter(prefix="/hub", tags=["hub"])


@customer_briefing_router.get("/calls/{call_id}/briefing", response_model=CustomerBriefingResponse)
async def get_customer_briefing(
    call_id: str,
    use_case: CustomerBriefingUseCase = Depends(get_customer_briefing_use_case),
) -> CustomerBriefingResponse:
    try:
        b = await use_case.get(call_id)
    except BriefingCallNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return CustomerBriefingResponse(
        call_id=b.call_id,
        status=b.status,
        prior_call_count=b.prior_call_count,
        purpose=None if b.purpose is None else BriefingPurposeSchema(
            category=b.purpose.category, text=b.purpose.text, source=b.purpose.source),
        briefing_lines=list(b.lines),
        evidence=[BriefingEvidenceSchema(call_id=p.call_id, started_at=p.started_at.isoformat(),
                                         inquiry_type=p.inquiry_type, summary_confirmed=p.summary_confirmed,
                                         incomplete_procedures=list(p.incomplete_procedures))
                  for p in b.evidence],
        signals=BriefingSignalsSchema(open_follow_ups=b.open_follow_ups,
                                      call_guard_categories=list(b.call_guard_categories),
                                      blacklisted=b.blacklisted),
        generated_at=b.generated_at.isoformat(),
    )
