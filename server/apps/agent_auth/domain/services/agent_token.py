# Requirement: J-1, SEC-1, SEC-2
"""상담원 토큰 — 만들고, 저장용 해시로 바꾼다. 표준 라이브러리뿐이다 (`decisions/307`).

**원문은 발급 응답으로 한 번만 나가고 어디에도 저장하지 않는다.** DB 에는 SHA-256 hex 만 둔다 —
`admin_refresh_token` 과 같은 원칙이다(탈취되는 값을 그대로 저장하지 않는다).

키(pepper) 없이 SHA-256 을 쓰는 이유: 전화번호(`decisions/304`)와 달리 토큰은 **256비트 난수**라
전수 대입으로 되돌릴 수 없다. 그래서 새 비밀 설정이 필요 없다.
"""

from __future__ import annotations

import hashlib
import secrets

TOKEN_PREFIX = "cga_"  # CallGuard Agent — 로그·유출 스캔에서 무엇인지 알아보게 한다
_TOKEN_BYTES = 32


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def looks_like_token(value: str) -> bool:
    """접두어가 다른 값(관리자 JWT 등)은 DB 를 조회하지 않고 거절한다."""
    return value.startswith(TOKEN_PREFIX) and len(value) > len(TOKEN_PREFIX)
