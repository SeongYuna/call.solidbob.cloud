# Requirement: J-1
from __future__ import annotations

from abc import ABC, abstractmethod

from agent_auth.app.dtos.agent_directory_dto import AgentSummary


class AgentDirectoryPort(ABC):
    """`agent` 테이블 자체를 읽는다 — 발급하는 쪽(`agent_token`)과는 다른 포트다."""

    @abstractmethod
    async def list(self) -> list[AgentSummary]: ...
