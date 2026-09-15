# Requirement: B-5, E-1
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.recommendation_card_dto import RecommendationCards


class RecommendationRecordPort(ABC):
    """발동한 추천 1회를 남긴다 — `recommendation` 1행 + 카드마다 `recommendation_card` 1행.

    돌려주는 것은 **카드 순서 그대로의 `card_id`** 다(배열 순서 = rank). 카드 피드백(`POST /hub/cards/{card_id}/feedback`)이
    이 값으로 카드를 가리킨다. 저장하지 않는 구현(로그)은 None 을 채워 돌려준다 — id 를 지어내지 않는다.
    """

    @abstractmethod
    async def record(self, cards: RecommendationCards) -> tuple[int | None, ...]:
        """통화(`call`)가 없으면 `CallNotStartedError`. 저장소가 외래키를 모르면(로그 어댑터) 올리지 않는다."""
