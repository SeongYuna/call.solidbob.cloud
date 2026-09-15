# Requirement: J-5
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.routing_decision_dto import RoutedCall, RoutingDecisionCommand


class RoutingDecisionUseCase(ABC):
    """인입 전 배정 판정 — 블랙리스트 고객이면 베테랑을 고른다. 실제 연결은 부르는 쪽(교환기)이 한다."""

    @abstractmethod
    async def decide(self, command: RoutingDecisionCommand) -> RoutedCall: ...
