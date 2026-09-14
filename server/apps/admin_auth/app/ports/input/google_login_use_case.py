# Requirement: 관리자 로그인(구글)
from __future__ import annotations

from abc import ABC, abstractmethod

from admin_auth.app.dtos.token_pair_dto import IssuedTokenPair


class GoogleLoginUseCase(ABC):
    """구글 id_token → (관리자 확인) → access/refresh token 발급.

    InvalidGoogleTokenError(토큰 자체가 틀림) · NotAnAdminError(구글 인증은 됐지만
    허용 목록에 없음)를 던질 수 있다 — 회원가입이 없으므로 후자가 최종 판단이다."""

    @abstractmethod
    async def login(self, id_token: str) -> IssuedTokenPair: ...
