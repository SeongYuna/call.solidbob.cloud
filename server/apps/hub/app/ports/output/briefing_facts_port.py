# Requirement: F-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.customer_briefing_dto import BriefingFacts


class BriefingFactsPort(ABC):
    """이번 통화의 고객으로 **이번 통화보다 앞선** 통화 사실을 모은다. 없는 통화면 None."""

    @abstractmethod
    async def collect(self, call_id: str) -> BriefingFacts | None: ...
