# Requirement: J-1
from __future__ import annotations

from abc import ABC, abstractmethod

from agent_auth.app.dtos.agent_directory_dto import AgentSummary


class AgentDirectoryListUseCase(ABC):
    """이름으로 고를 상담원 후보 목록 — 관리자가 토큰 발급 대상을 ID 대신 이름으로 찾는 화면용."""

    @abstractmethod
    async def list(self) -> list[AgentSummary]: ...
