# Requirement: 관리자 로그인(구글)
from __future__ import annotations

from abc import ABC, abstractmethod

from admin_auth.app.dtos.token_pair_dto import IssuedTokenPair


class RefreshUseCase(ABC):
    """refresh token → 새 access/refresh token 쌍. 기존 refresh token은 회전으로 즉시 무효화된다.

    InvalidRefreshTokenError를 던질 수 있다(없음·만료·이미 회전됨을 구분하지 않는다 —
    구분해서 알려주면 토큰 추측 공격에 힌트를 준다)."""

    @abstractmethod
    async def refresh(self, refresh_token: str) -> IssuedTokenPair: ...
