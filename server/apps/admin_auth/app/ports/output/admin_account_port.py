# Requirement: 관리자 로그인(구글)
from __future__ import annotations

from abc import ABC, abstractmethod

from admin_auth.app.dtos.admin_identity_dto import AdminAccount


class AdminAccountPort(ABC):
    """`admin_account` 허용 목록 조회. 여기 없는 이메일은 구글 인증을 통과해도 관리자가 아니다."""

    @abstractmethod
    async def find_by_email(self, email: str) -> AdminAccount | None: ...

    @abstractmethod
    async def find_by_id(self, account_id: int) -> AdminAccount | None: ...

    @abstractmethod
    async def link_agent(self, account_id: int, agent_id: str) -> str:
        """`agent_id` 가 비어 있을 때만 채우고, 실제로 남은 값을 돌려준다(`decisions/314`).

        이미 값이 있으면 덮어쓰지 않는다 — 동시에 두 요청이 들어와도 먼저 쓴 값이 이긴다.
        """
        ...
