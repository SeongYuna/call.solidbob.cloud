# Requirement: 관리자 로그인(구글), QUA-1
"""회전(rotation) — refresh 성공/실패 모두 기존 토큰은 다시 못 쓴다."""

import asyncio

import pytest

from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.dtos.errors import InvalidRefreshTokenError
from admin_auth.app.dtos.token_pair_dto import IssuedAccessToken, IssuedRefreshToken
from admin_auth.app.ports.output.access_token_issuer_port import AccessTokenIssuerPort
from admin_auth.app.ports.output.admin_account_port import AdminAccountPort
from admin_auth.app.ports.output.refresh_token_port import RefreshTokenPort, RefreshTokenRecord
from admin_auth.app.use_cases.refresh_interactor import RefreshInteractor


class _FakeRefreshTokens(RefreshTokenPort):
    def __init__(self, valid_for: dict[str, int]) -> None:
        self._valid_for = dict(valid_for)
        self.revoked: list[str] = []
        self.issued_for: list[int] = []

    async def issue(self, admin_account_id: int) -> IssuedRefreshToken:
        self.issued_for.append(admin_account_id)
        return IssuedRefreshToken(token=f"new-refresh-{admin_account_id}", expires_in=600)

    async def find_valid(self, raw_token: str):
        account_id = self._valid_for.get(raw_token)
        return None if account_id is None else RefreshTokenRecord(admin_account_id=account_id)

    async def revoke(self, raw_token: str) -> None:
        self.revoked.append(raw_token)
        self._valid_for.pop(raw_token, None)


class _FakeAccounts(AdminAccountPort):
    def __init__(self, accounts: dict[int, AdminAccount]) -> None:
        self._by_id = accounts

    async def find_by_email(self, email: str):
        raise NotImplementedError

    async def find_by_id(self, account_id: int) -> AdminAccount | None:
        return self._by_id.get(account_id)


class _FakeAccessIssuer(AccessTokenIssuerPort):
    async def issue(self, account: AdminAccount) -> IssuedAccessToken:
        return IssuedAccessToken(token=f"access-{account.id}", jti=f"jti-{account.id}", expires_in=300)

    async def decode(self, token: str):
        raise NotImplementedError

    async def revoke(self, jti: str) -> None:
        raise NotImplementedError


def test_유효한_refresh_token은_새_쌍을_발급하고_기존_것을_회전시킨다():
    refresh_tokens = _FakeRefreshTokens({"old-token": 1})
    accounts = _FakeAccounts({1: AdminAccount(id=1, email="admin@example.com", name=None)})
    interactor = RefreshInteractor(refresh_tokens, accounts, _FakeAccessIssuer())

    pair = asyncio.run(interactor.refresh("old-token"))

    assert pair.access_token == "access-1"
    assert pair.refresh_token == "new-refresh-1"
    assert refresh_tokens.revoked == ["old-token"]  # 성공해도 기존 토큰은 무효화된다
    assert refresh_tokens.issued_for == [1]


def test_없거나_만료된_refresh_token은_InvalidRefreshTokenError():
    interactor = RefreshInteractor(_FakeRefreshTokens({}), _FakeAccounts({}), _FakeAccessIssuer())
    with pytest.raises(InvalidRefreshTokenError):
        asyncio.run(interactor.refresh("unknown-token"))


def test_토큰은_유효해도_계정이_지워졌으면_InvalidRefreshTokenError():
    refresh_tokens = _FakeRefreshTokens({"old-token": 999})
    interactor = RefreshInteractor(refresh_tokens, _FakeAccounts({}), _FakeAccessIssuer())
    with pytest.raises(InvalidRefreshTokenError):
        asyncio.run(interactor.refresh("old-token"))
    assert refresh_tokens.revoked == ["old-token"]  # 계정이 없어도 회전은 이미 끝난 뒤다
