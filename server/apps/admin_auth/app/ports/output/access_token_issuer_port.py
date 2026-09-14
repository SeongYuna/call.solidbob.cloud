# Requirement: 관리자 로그인(구글)
from __future__ import annotations

from abc import ABC, abstractmethod

from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.dtos.token_pair_dto import DecodedAccessToken, IssuedAccessToken


class AccessTokenIssuerPort(ABC):
    """JWT access token 발급·검증·즉시무효화. 서명 자체는 오래 유효해도(exp) 세션 존재 여부는
    Redis가 판단한다 — 로그아웃이 exp 전에 즉시 반영되려면 서명 검증만으로는 부족하다."""

    @abstractmethod
    async def issue(self, account: AdminAccount) -> IssuedAccessToken: ...

    @abstractmethod
    async def decode(self, token: str) -> DecodedAccessToken | None:
        """서명·만료가 유효하고 세션이 아직 살아있으면 해석 결과를, 아니면 None을 돌려준다."""
        ...

    @abstractmethod
    async def revoke(self, jti: str) -> None:
        """로그아웃 — 세션을 즉시 지운다(서명 자체는 그대로 exp까지 유효하지만 decode가 더 이상 통과시키지 않는다)."""
        ...
