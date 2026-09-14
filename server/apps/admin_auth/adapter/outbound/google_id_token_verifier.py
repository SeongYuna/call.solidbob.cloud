# Requirement: 관리자 로그인(구글)
"""GoogleIdentityPort의 구글 공식 라이브러리 구현. 서명·issuer·audience·만료를 전부
`google.oauth2.id_token.verify_oauth2_token`에 맡긴다 — 직접 JWT를 파싱하지 않는다
(서명 검증을 직접 구현하면 틀리기 쉽다)."""

from __future__ import annotations

import asyncio

from admin_auth.app.dtos.admin_identity_dto import GoogleIdentity
from admin_auth.app.dtos.errors import InvalidGoogleTokenError
from admin_auth.app.ports.output.google_identity_port import GoogleIdentityPort

_VALID_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


class GoogleIdTokenVerifier(GoogleIdentityPort):
    def __init__(self, client_id: str) -> None:
        self._client_id = client_id

    async def verify(self, id_token: str) -> GoogleIdentity:
        from google.auth.transport import requests as google_requests  # noqa: PLC0415
        from google.oauth2 import id_token as google_id_token  # noqa: PLC0415

        def _verify() -> dict:
            return google_id_token.verify_oauth2_token(
                id_token, google_requests.Request(), self._client_id
            )

        try:
            claims = await asyncio.to_thread(_verify)
        except ValueError as exc:  # google-auth가 검증 실패를 전부 ValueError로 던진다
            raise InvalidGoogleTokenError(str(exc)) from exc

        if claims.get("iss") not in _VALID_ISSUERS:
            raise InvalidGoogleTokenError("issuer가 구글이 아니다")
        email = claims.get("email")
        if not email or not claims.get("email_verified"):
            raise InvalidGoogleTokenError("이메일이 없거나 구글에서 검증되지 않은 계정이다")

        return GoogleIdentity(email=email.lower(), name=claims.get("name"))
