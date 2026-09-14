# Requirement: 관리자 로그인(구글), SEC-2
"""admin_auth 포트 → 구체 구현 배선. 필요한 설정이 없으면 조용히 대체 구현으로 넘어가지
않고 **RuntimeError로 막는다** — 인증은 "일단 되게" 하려고 가짜 구현을 넣으면 그게 곧
누구나 로그인되는 구멍이 된다(hub의 다른 프로바이더들이 Log 어댑터로 대체하는 것과 달리,
여기는 실패를 명확히 드러내는 쪽을 택한다)."""

from __future__ import annotations

from fastapi import Request

from admin_auth.adapter.outbound.google_id_token_verifier import GoogleIdTokenVerifier
from admin_auth.adapter.outbound.postgres.admin_account_repository import (
    PostgresAdminAccountRepository,
)
from admin_auth.adapter.outbound.postgres.admin_refresh_token_repository import (
    PostgresRefreshTokenRepository,
)
from admin_auth.adapter.outbound.redis.redis_jwt_access_token_issuer import (
    RedisJwtAccessTokenIssuer,
)
from admin_auth.app.ports.output.access_token_issuer_port import AccessTokenIssuerPort
from admin_auth.app.ports.output.admin_account_port import AdminAccountPort
from admin_auth.app.ports.output.google_identity_port import GoogleIdentityPort
from admin_auth.app.ports.output.refresh_token_port import RefreshTokenPort
from hub.adapter.outbound.postgres.connection import build_connection_factory

_redis_client_singleton = None  # 커넥션 풀을 요청마다 새로 만들지 않는다


def get_google_identity_port(request: Request) -> GoogleIdentityPort:
    settings = request.app.state.settings
    if not settings.google_oauth_client_id:
        raise RuntimeError("GOOGLE_OAUTH_CLIENT_ID가 없습니다 — .env를 확인하세요 (SEC-2)")
    return GoogleIdTokenVerifier(client_id=settings.google_oauth_client_id)


def get_admin_account_port(request: Request) -> AdminAccountPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise RuntimeError("PostgreSQL 설정이 없습니다 — .env의 DATABASE_URL을 확인하세요 (SEC-2)")
    return PostgresAdminAccountRepository(build_connection_factory(settings))


def get_refresh_token_port(request: Request) -> RefreshTokenPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise RuntimeError("PostgreSQL 설정이 없습니다 — .env의 DATABASE_URL을 확인하세요 (SEC-2)")
    return PostgresRefreshTokenRepository(
        build_connection_factory(settings),
        ttl_seconds=settings.admin_refresh_token_ttl_seconds,
    )


def _redis_client(redis_url: str):
    global _redis_client_singleton  # noqa: PLW0603
    if _redis_client_singleton is None:
        import redis.asyncio as redis  # noqa: PLC0415

        _redis_client_singleton = redis.from_url(redis_url, decode_responses=True)
    return _redis_client_singleton


def get_access_token_issuer_port(request: Request) -> AccessTokenIssuerPort:
    settings = request.app.state.settings
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL이 없습니다 — .env를 확인하세요 (테스트용 로컬 redis, SEC-2)")
    if not settings.admin_jwt_secret:
        raise RuntimeError("ADMIN_JWT_SECRET이 없습니다 — .env를 확인하세요 (SEC-2)")
    return RedisJwtAccessTokenIssuer(
        redis_client=_redis_client(settings.redis_url),
        jwt_secret=settings.admin_jwt_secret,
        ttl_seconds=settings.admin_access_token_ttl_seconds,
    )
