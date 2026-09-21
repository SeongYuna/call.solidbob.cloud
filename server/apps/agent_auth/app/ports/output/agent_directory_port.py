# Requirement: J-1
from __future__ import annotations

from abc import ABC, abstractmethod

from agent_auth.app.dtos.agent_directory_dto import AgentSummary


class AgentDirectoryPort(ABC):
    """`agent` 테이블 자체를 읽는다 — 발급하는 쪽(`agent_token`)과는 다른 포트다."""

    @abstractmethod
    async def list(self) -> list[AgentSummary]: ...

    @abstractmethod
    async def get(self, agent_id: str) -> AgentSummary | None:
        """`agent_id` 그대로 하나 찾는다 — 없으면 `None`. `resolve_or_create`와 달리 만들지 않는다."""
        ...

    @abstractmethod
    async def resolve_or_create(self, identifier: str) -> AgentSummary:
        """`agent_id` 또는 `display_name` 으로 먼저 찾고, 없으면 그 이름으로 새 상담원을 만든다.

        상담원 목록 관리 화면이 아직 없다(테스트 단계, `decisions/406`) — 관리자가 토큰 발급
        화면에 이름을 치면 그 자리에서 만들어진다.
        """
        ...
