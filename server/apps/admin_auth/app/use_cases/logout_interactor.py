# Requirement: 관리자 로그인(구글)
"""access token은 이미 만료·위조됐을 수도 있다 — decode가 None이면 그냥 넘어간다.
로그아웃은 "지금 세션을 확실히 끊는다"가 목적이지 토큰 유효성 검사가 목적이 아니다."""

from __future__ import annotations

from admin_auth.app.ports.input.logout_use_case import LogoutUseCase
from admin_auth.app.ports.output.access_token_issuer_port import AccessTokenIssuerPort
from admin_auth.app.ports.output.refresh_token_port import RefreshTokenPort


class LogoutInteractor(LogoutUseCase):
    def __init__(self, access_issuer: AccessTokenIssuerPort, refresh_tokens: RefreshTokenPort) -> None:
        self._access_issuer = access_issuer
        self._refresh_tokens = refresh_tokens

    async def logout(self, access_token: str | None, refresh_token: str | None) -> None:
        if access_token:
            decoded = await self._access_issuer.decode(access_token)
            if decoded is not None:
                await self._access_issuer.revoke(decoded.jti)
        if refresh_token:
            await self._refresh_tokens.revoke(refresh_token)
