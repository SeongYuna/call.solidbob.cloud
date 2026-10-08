# Requirement: F-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.customer_briefing_dto import CustomerBriefing


class CustomerBriefingUseCase(ABC):
    """통화 수신 전 고객 브리핑(`decisions/220`). 없는 통화면 `BriefingCallNotFound`."""

    @abstractmethod
    async def get(self, call_id: str) -> CustomerBriefing: ...
