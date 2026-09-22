# Requirement: J-5
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from agent_auth.app.dtos.agent_directory_dto import AgentHiredOnCommand, AgentSummary
from agent_auth.app.ports.input.agent_hired_on_use_case import AgentHiredOnUseCase
from agent_auth.app.ports.output.agent_directory_port import AgentDirectoryPort


class AgentHiredOnInteractor(AgentHiredOnUseCase):
    def __init__(self, agents: AgentDirectoryPort, today: Callable[[], date] = date.today) -> None:
        self._agents = agents
        self._today = today

    async def set(self, command: AgentHiredOnCommand) -> AgentSummary | None:
        # 입력 범위 검사다(근속 기준 0.5~40년과 같은 자리) — 베테랑 판정은 블랙리스트 도메인 `route()` 몫이다
        if command.hired_on is not None and command.hired_on > self._today():
            raise ValueError(f"입사일이 오늘보다 뒤입니다: {command.hired_on.isoformat()}")
        return await self._agents.set_hired_on(command.agent_id, command.hired_on)
