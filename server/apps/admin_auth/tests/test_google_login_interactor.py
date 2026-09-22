# Requirement: 관리자 로그인(구글), QUA-1
"""페이크 포트로 인터랙터만 검증 — 회원가입 없이 admin_account 존재 여부만 판정하는지."""

import asyncio

import pytest

from admin_auth.app.dtos.admin_identity_dto import AdminAccount, GoogleIdentity
from admin_auth.app.dtos.errors import NotAnAdminError
from admin_auth.app.dtos.token_pair_dto import IssuedAccessToken, IssuedRefreshToken
from admin_auth.app.ports.output.access_token_issuer_port import AccessTokenIssuerPort
from admin_auth.app.ports.output.admin_account_port import AdminAccountPort
from admin_auth.app.ports.output.google_identity_port import GoogleIdentityPort
from admin_auth.app.ports.output.refresh_token_port import RefreshTokenPort
from admin_auth.app.use_cases.google_login_interactor import GoogleLoginInteractor


class _FakeIdentity(GoogleIdentityPort):
    def __init__(self, email: str) -> None:
        self._email = email

    async def verify(self, id_token: str) -> GoogleIdentity:
        return GoogleIdentity(email=self._email, name="테스트")


class _FakeAccounts(AdminAccountPort):
    def __init__(self, accounts: dict[str, AdminAccount]) -> None:
        self._by_email = accounts

    async def find_by_email(self, email: str) -> AdminAccount | None:
        return self._by_email.get(email)

    async def find_by_id(self, account_id: int) -> AdminAccount | None:
        return next((a for a in self._by_email.values() if a.id == account_id), None)

    async def link_agent(self, account_id: int, agent_id: str) -> str:
        raise NotImplementedError


class _FakeAccessIssuer(AccessTokenIssuerPort):
    async def issue(self, account: AdminAccount) -> IssuedAccessToken:
        return IssuedAccessToken(token=f"access-{account.id}", jti=f"jti-{account.id}", expires_in=300)

    async def decode(self, token: str):
        raise NotImplementedError

    async def revoke(self, jti: str) -> None:
        raise NotImplementedError


class _FakeRefreshTokens(RefreshTokenPort):
    async def issue(self, admin_account_id: int) -> IssuedRefreshToken:
        return IssuedRefreshToken(token=f"refresh-{admin_account_id}", expires_in=600)

    async def find_valid(self, raw_token: str):
        raise NotImplementedError

    async def revoke(self, raw_token: str) -> None:
        raise NotImplementedError


def _interactor(accounts: dict[str, AdminAccount], email: str = "admin@example.com") -> GoogleLoginInteractor:
    return GoogleLoginInteractor(
        identity=_FakeIdentity(email),
        accounts=_FakeAccounts(accounts),
        access_issuer=_FakeAccessIssuer(),
        refresh_tokens=_FakeRefreshTokens(),
    )


def test_허용_목록에_있으면_토큰_쌍을_발급한다():
    account = AdminAccount(id=1, email="admin@example.com", name="관리자")
    pair = asyncio.run(_interactor({"admin@example.com": account}).login("dummy-id-token"))
    assert pair.access_token == "access-1"
    assert pair.access_token_expires_in == 300
    assert pair.refresh_token == "refresh-1"
    assert pair.refresh_token_expires_in == 600


def test_허용_목록에_없으면_NotAnAdminError():
    with pytest.raises(NotAnAdminError):
        asyncio.run(_interactor({}, email="outsider@example.com").login("dummy-id-token"))
