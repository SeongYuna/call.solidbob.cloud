# Requirement: J-4, 관리자 로그인(구글)
from __future__ import annotations

from abc import ABC, abstractmethod

from admin_auth.app.dtos.admin_identity_dto import AdminAccount


class AdminAgentLinkUseCase(ABC):
    """관리자의 블랙리스트 결정을 기록할 상담원 마스터 ID 를 돌려준다(`decisions/314`, `304`).

    연결이 없으면 그 자리에서 관리자 전용 `agent` 행을 붙인다 — 운영자가 SQL 로 채우기를 기다리지 않는다.
    """

    @abstractmethod
    async def resolve(self, admin: AdminAccount) -> str: ...
