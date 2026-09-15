# Requirement: B-5, E-1
"""PostgreSQL 이 없을 때의 추천 기록. 건수·지연만 남기고 카드 id 는 없다(None) — 피드백을 받을 수 없다는 것이 그대로 드러난다."""

from __future__ import annotations

import logging

from hub.app.dtos.recommendation_card_dto import RecommendationCards
from hub.app.ports.output.recommendation_record_port import RecommendationRecordPort

logger = logging.getLogger(__name__)


class LogRecommendationRecordAdapter(RecommendationRecordPort):
    async def record(self, cards: RecommendationCards) -> tuple[int | None, ...]:
        logger.info(
            "recommendation fired call_id=%s cards=%d internal_latency_ms=%s",
            cards.call_id, len(cards.cards), cards.internal_latency_ms,
        )
        return tuple(None for _ in cards.cards)
