# Requirement: J-5
"""POST /hub/routing-decisions — 인입 전 배정 판정(`decisions/313`). 블랙리스트 고객이면 근속 기준 이상 상담사를 고른다.

순서: `POST /hub/calls`(발신 번호 → 고객 식별) → 여기 → 부르는 쪽이 상담사 연결. 결과는 `routing_log` 에 남는다.
인증은 통화 시작과 같다(없음) — 부르는 쪽이 교환기·콜 미디에이터다. 통화가 없으면 404 · DB 없음 501.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.routing_decision_schema import RoutingDecisionRequest, RoutingDecisionResponse
from hub.app.dtos.routing_decision_dto import RoutingDecisionCommand
from hub.app.ports.input.routing_decision_use_case import RoutingDecisionUseCase
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.routing_decision_provider import get_routing_decision_use_case

routing_decision_router = APIRouter(prefix="/hub", tags=["hub"])


@routing_decision_router.post("/routing-decisions", response_model=RoutingDecisionResponse)
async def decide_routing(
    body: RoutingDecisionRequest,
    use_case: RoutingDecisionUseCase = Depends(get_routing_decision_use_case),
) -> RoutingDecisionResponse:
    try:
        routed = await use_case.decide(RoutingDecisionCommand(call_id=body.call_id, candidate_ids=tuple(body.candidates)))
    except CallNotStartedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"통화가 없습니다: {body.call_id} — POST /hub/calls 가 먼저 와야 한다") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    d = routed.decision
    return RoutingDecisionResponse(
        call_id=routed.call_id, assigned_agent_id=d.agent_id, is_blacklisted=d.is_blacklisted, fell_back=d.fell_back,
        reason=d.reason, customer_identified=routed.customer_identified, veteran_years=routed.veteran_years,
        unknown_candidates=list(routed.unknown_candidates))
