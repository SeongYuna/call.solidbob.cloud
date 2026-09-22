# Requirement: E-1
"""POST /hub/cards/{card_id}/feedback — 추천 카드 채택·무시 기록.

**상담원 토큰을 확인하되 누구인지는 버린다**(`_project/decisions/315`). 전에는 문이 없어 누구나 피드백을 쓸 수 있었다.
그렇다고 상담원을 받으면 카드 품질 데이터가 상담원 줄 세우기 데이터가 된다(부록 A-1, `CardFeedback` 주석).
`dependencies=[...]` 로 걸어 가드의 반환값(agent_id)이 **이 함수에 아예 들어오지 않는다** — 넘길 수 없으니 저장할 수도 없다.
"""

from __future__ import annotations

from agent_auth.adapter.inbound.api.agent_guard import require_agent
from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.card_feedback_schema import (
    CardFeedbackRequest,
    CardFeedbackResponse,
)
from hub.app.dtos.card_feedback_dto import CardFeedback
from hub.app.ports.input.card_feedback_use_case import CardFeedbackUseCase
from hub.dependencies.card_feedback_provider import get_card_feedback_use_case

card_feedback_router = APIRouter(prefix="/hub", tags=["hub"])


@card_feedback_router.post(
    "/cards/{card_id}/feedback",
    response_model=CardFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_agent)],  # 확인만 — 반환값을 받지 않는다
)
async def record_card_feedback(
    card_id: int,
    body: CardFeedbackRequest,
    use_case: CardFeedbackUseCase = Depends(get_card_feedback_use_case),
) -> CardFeedbackResponse:
    try:
        receipt = await use_case.record(CardFeedback(card_id=card_id, action=body.action))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return CardFeedbackResponse(
        feedback_id=receipt.feedback_id, card_id=receipt.card_id, action=receipt.action
    )
