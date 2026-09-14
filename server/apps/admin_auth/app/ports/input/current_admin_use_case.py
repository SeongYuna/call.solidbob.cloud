# Requirement: 관리자 로그인(구글)
from __future__ import annotations

from abc import ABC, abstractmethod

from admin_auth.app.dtos.admin_identity_dto import AdminAccount


class CurrentAdminUseCase(ABC):
    """access token → 현재 관리자. 세션이 없거나(로그아웃·만료) 계정이 지워졌으면 None."""

    @abstractmethod
    async def current(self, access_token: str) -> AdminAccount | None: ...
