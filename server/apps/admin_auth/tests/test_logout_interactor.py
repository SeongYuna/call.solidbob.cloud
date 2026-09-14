# Requirement: 관리자 로그인(구글), QUA-1
"""로그아웃은 멱등이다 — 이미 무효한 토큰이 와도 조용히 끝난다."""

import asyncio

from admin_auth.app.dtos.token_pair_dto import DecodedAccessToken
from admin_auth.app.ports.output.access_token_issuer_port import AccessTokenIssuerPort
from admin_auth.app.ports.output.refresh_token_port import RefreshTokenPort
from admin_auth.app.use_cases.logout_interactor import LogoutInteractor


class _FakeAccessIssuer(AccessTokenIssuerPort):
    def __init__(self, decodes_to: DecodedAccessToken | None) -> None:
        self._decodes_to = decodes_to
        self.revoked_jtis: list[str] = []

    async def issue(self, account):
        raise NotImplementedError

    async def decode(self, token: str):
        return self._decodes_to

    async def revoke(self, jti: str) -> None:
        self.revoked_jtis.append(jti)


class _FakeRefreshTokens(RefreshTokenPort):
    def __init__(self) -> None:
        self.revoked: list[str] = []

    async def issue(self, admin_account_id: int):
        raise NotImplementedError

    async def find_valid(self, raw_token: str):
        raise NotImplementedError

    async def revoke(self, raw_token: str) -> None:
        self.revoked.append(raw_token)


def test_유효한_토큰_둘_다_넘기면_둘_다_무효화한다():
    decoded = DecodedAccessToken(account_id=1, email="admin@example.com", jti="jti-1")
    access_issuer = _FakeAccessIssuer(decodes_to=decoded)
    refresh_tokens = _FakeRefreshTokens()

    asyncio.run(LogoutInteractor(access_issuer, refresh_tokens).logout("access-token", "refresh-token"))

    assert access_issuer.revoked_jtis == ["jti-1"]
    assert refresh_tokens.revoked == ["refresh-token"]


def test_이미_무효한_access_token은_조용히_넘어간다():
    access_issuer = _FakeAccessIssuer(decodes_to=None)  # decode 실패 — 이미 만료/위조
    refresh_tokens = _FakeRefreshTokens()

    asyncio.run(LogoutInteractor(access_issuer, refresh_tokens).logout("garbage", None))

    assert access_issuer.revoked_jtis == []  # decode가 None이라 revoke 자체를 안 부른다
    assert refresh_tokens.revoked == []


def test_아무것도_없으면_아무_일도_하지_않는다():
    access_issuer = _FakeAccessIssuer(decodes_to=None)
    refresh_tokens = _FakeRefreshTokens()

    asyncio.run(LogoutInteractor(access_issuer, refresh_tokens).logout(None, None))

    assert access_issuer.revoked_jtis == []
    assert refresh_tokens.revoked == []
