# Requirement: J-5
"""배정 판정 인터랙터 — 입력을 확인하고 포트에 넘긴다. **누가 베테랑인지·블랙리스트인지 판단하지 않는다**(포트 뒤 도메인 규칙)."""

from __future__ import annotations

from hub.app.dtos.routing_decision_dto import MAX_CANDIDATES, RoutedCall, RoutingDecisionCommand
from hub.app.ports.input.routing_decision_use_case import RoutingDecisionUseCase
from hub.app.ports.output.agent_routing_port import AgentRoutingPort


class RoutingDecisionInteractor(RoutingDecisionUseCase):
    def __init__(self, routing: AgentRoutingPort) -> None:
        self._routing = routing

    async def decide(self, command: RoutingDecisionCommand) -> RoutedCall:
        if not command.call_id.strip():
            raise ValueError("call_id 가 비어 있습니다")
        # 같은 상담사가 두 번 오면 한 번만 — 순서는 지킨다
        candidates = tuple(dict.fromkeys(c.strip() for c in command.candidate_ids if c.strip()))
        if len(candidates) > MAX_CANDIDATES:
            raise ValueError(f"후보는 {MAX_CANDIDATES}명까지입니다: {len(candidates)}")
        return await self._routing.route_call(command.call_id, candidates)
