# Requirement: 관리자 로그인(구글)
"""발급 결과 DTO. 원문 토큰은 여기서 한 번만 돌아다니고 저장소엔 남지 않는다(refresh는 해시만 저장)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IssuedAccessToken:
    token: str
    jti: str
    expires_in: int  # 초


@dataclass(frozen=True)
class IssuedRefreshToken:
    token: str
    expires_in: int  # 초


@dataclass(frozen=True)
class IssuedTokenPair:
    access_token: str
    access_token_expires_in: int
    refresh_token: str
    refresh_token_expires_in: int


@dataclass(frozen=True)
class DecodedAccessToken:
    """access token을 검증·해석한 결과. Redis 세션이 없으면(로그아웃·만료) None을 돌려준다 — 이 타입 자체는 안 나온다."""

    account_id: int
    email: str
    jti: str
