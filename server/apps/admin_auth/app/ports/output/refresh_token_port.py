# Requirement: 관리자 로그인(구글)
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from admin_auth.app.dtos.token_pair_dto import IssuedRefreshToken


@dataclass(frozen=True)
class RefreshTokenRecord:
    admin_account_id: int


class RefreshTokenPort(ABC):
    """`admin_refresh_token` — 원문은 저장하지 않고 해시만 둔다. 회전(rotation) 방식이라
    사용한 토큰은 매번 무효화하고 새로 발급한다."""

    @abstractmethod
    async def issue(self, admin_account_id: int) -> IssuedRefreshToken: ...

    @abstractmethod
    async def find_valid(self, raw_token: str) -> RefreshTokenRecord | None:
        """만료 전이고 아직 회전·로그아웃으로 무효화되지 않은 것만 돌려준다."""
        ...

    @abstractmethod
    async def revoke(self, raw_token: str) -> None: ...
