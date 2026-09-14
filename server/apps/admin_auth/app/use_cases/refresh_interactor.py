# Requirement: 관리자 로그인(구글)
"""회전(rotation): 들어온 refresh token은 성공 여부와 무관하게 다시 못 쓴다.
탈취된 토큰이 재사용되면 정상 사용자의 다음 refresh가 실패하면서 드러난다."""

from __future__ import annotations

from admin_auth.app.dtos.errors import InvalidRefreshTokenError
from admin_auth.app.dtos.token_pair_dto import IssuedTokenPair
from admin_auth.app.ports.input.refresh_use_case import RefreshUseCase
from admin_auth.app.ports.output.access_token_issuer_port import AccessTokenIssuerPort
from admin_auth.app.ports.output.admin_account_port import AdminAccountPort
from admin_auth.app.ports.output.refresh_token_port import RefreshTokenPort


class RefreshInteractor(RefreshUseCase):
    def __init__(
        self,
        refresh_tokens: RefreshTokenPort,
        accounts: AdminAccountPort,
        access_issuer: AccessTokenIssuerPort,
    ) -> None:
        self._refresh_tokens = refresh_tokens
        self._accounts = accounts
        self._access_issuer = access_issuer

    async def refresh(self, refresh_token: str) -> IssuedTokenPair:
        record = await self._refresh_tokens.find_valid(refresh_token)
        if record is None:
            raise InvalidRefreshTokenError()
        await self._refresh_tokens.revoke(refresh_token)

        account = await self._accounts.find_by_id(record.admin_account_id)
        if account is None:
            # 발급 뒤 admin_account 에서 지워졌다(관리자 해제) — refresh token 만 남아있던 경우
            raise InvalidRefreshTokenError()

        access = await self._access_issuer.issue(account)
        new_refresh = await self._refresh_tokens.issue(account.id)
        return IssuedTokenPair(
            access_token=access.token,
            access_token_expires_in=access.expires_in,
            refresh_token=new_refresh.token,
            refresh_token_expires_in=new_refresh.expires_in,
        )
