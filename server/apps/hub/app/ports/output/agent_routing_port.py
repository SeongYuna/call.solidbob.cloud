# Requirement: J-5
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.routing_decision_dto import RoutedCall


class AgentRoutingPort(ABC):
    """통화 1건의 배정을 판정하고 `routing_log` 에 남긴다(`decisions/313`).

    구현이 통화의 고객 식별자로 적용 중 블랙리스트를 확인하고, 후보의 입사일로 근속을 세고, 저장된 베테랑 기준을 읽어
    **블랙리스트 도메인 규칙**(`routing.route`)에 맡긴다 — 허브는 판정하지 않는다(절대 원칙 9 와 같은 배치).
    통화가 없으면 `CallNotStartedError`.
    """

    @abstractmethod
    async def route_call(self, call_id: str, candidate_ids: tuple[str, ...]) -> RoutedCall: ...
