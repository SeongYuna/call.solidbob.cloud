# Requirement: F-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.customer_briefing_dto import BriefingComposition, BriefingFacts


class CustomerBriefingPort(ABC):
    """사실 → 목적 추정 + 브리핑 줄. 지난 통화가 1건 이상일 때만 불린다. 모델 추론일 수 있어 async."""

    @abstractmethod
    async def compose(self, facts: BriefingFacts) -> BriefingComposition: ...
