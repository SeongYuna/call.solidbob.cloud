# Requirement: 관리자 로그인(구글)
"""AccessTokenIssuerPort의 구현 — 서명은 JWT(PyJWT), 세션 존재 여부는 Redis.

**왜 둘 다 필요한가.** JWT 서명만으로는 로그아웃이 즉시 반영되지 않는다 — exp가 되기 전까지는
서명이 그대로 유효하기 때문이다. 그래서 발급할 때마다 Redis에 `jti`를 키로 하는 세션 마커를
같이 심고(TTL = access token 만료와 동일), decode()가 서명 검증 다음에 그 마커의 존재까지
확인한다. revoke()는 그 마커를 지우는 것뿐이다 — JWT 자체를 무효화할 방법은 없으니 세션
쪽에서 끊는다.

**테스트 전용 스코프(2026-09-14 사용자 지시).** access token 5분 TTL은 "테스트만 진행"이라는
전제로 짧게 잡은 값이다 — Redis는 로컬 개발 컴포즈 패턴(`infra/README.md` "로컬 개발" 절)과
같은 방식으로 `docker run`으로 띄우는 것을 전제한다. `infra/CLAUDE.md` §1-2가 금지하는 것은
AWS ElastiCache(관리형 Redis)이지 로컬 컨테이너가 아니다 — 운영(k3s) 배포 매니페스트는 이
작업 범위에 포함하지 않았다.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.dtos.token_pair_dto import DecodedAccessToken, IssuedAccessToken
from admin_auth.app.ports.output.access_token_issuer_port import AccessTokenIssuerPort

_SESSION_KEY_PREFIX = "admin_access_session:"


class RedisJwtAccessTokenIssuer(AccessTokenIssuerPort):
    def __init__(self, redis_client, jwt_secret: str, ttl_seconds: int) -> None:
        self._redis = redis_client
        self._jwt_secret = jwt_secret
        self._ttl_seconds = ttl_seconds

    async def issue(self, account: AdminAccount) -> IssuedAccessToken:
        import jwt  # noqa: PLC0415  (adapter 전용 의존성)

        jti = secrets.token_urlsafe(16)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._ttl_seconds)
        token = jwt.encode(
            {
                "sub": str(account.id),
                "email": account.email,
                "jti": jti,
                "iat": now,
                "exp": expires_at,
            },
            self._jwt_secret,
            algorithm="HS256",
        )
        await self._redis.set(
            f"{_SESSION_KEY_PREFIX}{jti}", str(account.id), ex=self._ttl_seconds
        )
        return IssuedAccessToken(token=token, jti=jti, expires_in=self._ttl_seconds)

    async def decode(self, token: str) -> DecodedAccessToken | None:
        import jwt  # noqa: PLC0415

        try:
            claims = jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError:
            return None

        jti = claims.get("jti")
        session_account_id = await self._redis.get(f"{_SESSION_KEY_PREFIX}{jti}")
        if session_account_id is None:
            return None  # 서명은 유효해도 세션이 없다 — 로그아웃됐거나 Redis가 먼저 만료시켰다

        return DecodedAccessToken(account_id=int(claims["sub"]), email=claims["email"], jti=jti)

    async def revoke(self, jti: str) -> None:
        await self._redis.delete(f"{_SESSION_KEY_PREFIX}{jti}")
