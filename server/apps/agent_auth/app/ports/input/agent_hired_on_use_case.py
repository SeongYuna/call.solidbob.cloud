# Requirement: J-5
from __future__ import annotations

from abc import ABC, abstractmethod

from agent_auth.app.dtos.agent_directory_dto import AgentHiredOnCommand, AgentSummary


class AgentHiredOnUseCase(ABC):
    """관리자가 상담원 입사일을 넣는다 — J-5 베테랑 판정의 근속 재료(`decisions/321`)."""

    @abstractmethod
    async def set(self, command: AgentHiredOnCommand) -> AgentSummary | None:
        """없는 상담원이면 `None`. 오늘보다 뒤면 `ValueError`."""
        ...
