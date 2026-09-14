# Requirement: 관리자 로그인(구글)
"""판정은 하나뿐이다 — 「이 이메일이 admin_account에 있는가」. 그것도 저장소 조회지 규칙
엔진이 아니다. 그 외엔 포트를 순서대로 부르기만 한다."""

from __future__ import annotations

from admin_auth.app.dtos.errors import NotAnAdminError
from admin_auth.app.dtos.token_pair_dto import IssuedTokenPair
from admin_auth.app.ports.input.google_login_use_case import GoogleLoginUseCase
from admin_auth.app.ports.output.access_token_issuer_port import AccessTokenIssuerPort
from admin_auth.app.ports.output.admin_account_port import AdminAccountPort
from admin_auth.app.ports.output.google_identity_port import GoogleIdentityPort
from admin_auth.app.ports.output.refresh_token_port import RefreshTokenPort


class GoogleLoginInteractor(GoogleLoginUseCase):
    def __init__(
        self,
        identity: GoogleIdentityPort,
        accounts: AdminAccountPort,
        access_issuer: AccessTokenIssuerPort,
        refresh_tokens: RefreshTokenPort,
    ) -> None:
        self._identity = identity
        self._accounts = accounts
        self._access_issuer = access_issuer
        self._refresh_tokens = refresh_tokens

    async def login(self, id_token: str) -> IssuedTokenPair:
        identity = await self._identity.verify(id_token)  # 실패하면 InvalidGoogleTokenError

        account = await self._accounts.find_by_email(identity.email)
        if account is None:
            raise NotAnAdminError(identity.email)

        access = await self._access_issuer.issue(account)
        refresh = await self._refresh_tokens.issue(account.id)
        return IssuedTokenPair(
            access_token=access.token,
            access_token_expires_in=access.expires_in,
            refresh_token=refresh.token,
            refresh_token_expires_in=refresh.expires_in,
        )
