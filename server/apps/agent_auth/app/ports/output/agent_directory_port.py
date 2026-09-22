# Requirement: J-1
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from agent_auth.app.dtos.agent_directory_dto import AgentSummary


class AgentDirectoryPort(ABC):
    """`agent` 테이블 자체를 읽는다 — 발급하는 쪽(`agent_token`)과는 다른 포트다."""

    @abstractmethod
    async def list(self) -> list[AgentSummary]:
        """토큰 발급 화면의 후보 — `role='agent'` 만. 관리자에게 붙은 행(`ensure_admin`)은 뺀다(`decisions/314`)."""
        ...

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

    @abstractmethod
    async def set_hired_on(self, agent_id: str, hired_on: date | None) -> AgentSummary | None:
        """상담원(`role='agent'`)의 입사일을 바꾼다 — J-5 근속이 이 값에서 나온다(`decisions/321`).

        없는 상담원·관리자 행이면 `None`. 관리자 행은 배정 후보가 아니다(`decisions/314`).
        """
        ...

    @abstractmethod
    async def ensure_admin(self, agent_id: str, display_name: str) -> AgentSummary:
        """관리자 한 명에게 붙일 `agent` 행(`role='admin'`)을 `agent_id` 그대로 찾거나 만든다(`decisions/314`).

        `resolve_or_create` 를 쓰지 않는 이유 — 그쪽은 **이름으로도** 찾는다. 관리자와 이름이 같은 상담원이
        있으면 관리자의 결정이 그 상담원 이름으로 기록된다. 여기는 `agent_id`(`admin-<계정 id>`)로만 찾는다.
        """
        ...
