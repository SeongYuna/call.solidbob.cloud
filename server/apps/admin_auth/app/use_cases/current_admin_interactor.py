# Requirement: 관리자 로그인(구글)
from __future__ import annotations

from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.ports.input.current_admin_use_case import CurrentAdminUseCase
from admin_auth.app.ports.output.access_token_issuer_port import AccessTokenIssuerPort
from admin_auth.app.ports.output.admin_account_port import AdminAccountPort


class CurrentAdminInteractor(CurrentAdminUseCase):
    def __init__(self, access_issuer: AccessTokenIssuerPort, accounts: AdminAccountPort) -> None:
        self._access_issuer = access_issuer
        self._accounts = accounts

    async def current(self, access_token: str) -> AdminAccount | None:
        decoded = await self._access_issuer.decode(access_token)
        if decoded is None:
            return None
        return await self._accounts.find_by_id(decoded.account_id)
