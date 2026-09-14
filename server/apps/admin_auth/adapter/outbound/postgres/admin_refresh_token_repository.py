# Requirement: 관리자 로그인(구글), SEC-1
"""RefreshTokenPort의 PostgreSQL 구현. 원문 토큰은 발급 시 한 번 돌려주고 저장하지 않는다 —
저장하는 것은 SHA-256 해시뿐이다(탈취되는 값을 그대로 저장하지 않는다는 점에서 SEC-1과 같은 원칙)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from admin_auth.app.dtos.token_pair_dto import IssuedRefreshToken
from admin_auth.app.ports.output.refresh_token_port import RefreshTokenPort, RefreshTokenRecord
from hub.adapter.outbound.postgres.connection import ConnectionFactory

_INSERT = """
INSERT INTO "admin_refresh_token" ("admin_account_id", "token_hash", "issued_at", "expires_at")
VALUES (%s, %s, %s, %s)
"""
_SELECT_VALID = """
SELECT "admin_account_id" FROM "admin_refresh_token"
WHERE "token_hash" = %s AND "revoked_at" IS NULL AND "expires_at" > %s
"""
_REVOKE = 'UPDATE "admin_refresh_token" SET "revoked_at" = %s WHERE "token_hash" = %s'


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class PostgresRefreshTokenRepository(RefreshTokenPort):
    def __init__(self, connect: ConnectionFactory, ttl_seconds: int) -> None:
        self._connect = connect
        self._ttl_seconds = ttl_seconds

    async def issue(self, admin_account_id: int) -> IssuedRefreshToken:
        raw_token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._ttl_seconds)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_INSERT, (admin_account_id, _hash(raw_token), now, expires_at))
            await conn.commit()
        return IssuedRefreshToken(token=raw_token, expires_in=self._ttl_seconds)

    async def find_valid(self, raw_token: str) -> RefreshTokenRecord | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_SELECT_VALID, (_hash(raw_token), datetime.now(timezone.utc)))
                row = await cur.fetchone()
        if row is None:
            return None
        return RefreshTokenRecord(admin_account_id=row[0])

    async def revoke(self, raw_token: str) -> None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_REVOKE, (datetime.now(timezone.utc), _hash(raw_token)))
            await conn.commit()
