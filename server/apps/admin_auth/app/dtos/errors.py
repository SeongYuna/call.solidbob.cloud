# Requirement: 관리자 로그인(구글)
"""도메인 예외. 라우터가 이걸 HTTP 상태코드로 옮긴다 — 여기엔 상태코드를 두지 않는다
(app 계층은 fastapi를 모른다, .importlinter 계약 3)."""

from __future__ import annotations


class AdminAuthError(Exception):
    """관리자 인증 실패의 공통 부모."""


class InvalidGoogleTokenError(AdminAuthError):
    """구글 id_token 검증 실패 — 서명·issuer·audience·만료 중 하나가 틀렸다."""


class NotAnAdminError(AdminAuthError):
    """구글 인증은 됐지만 이 이메일이 admin_account에 없다. 회원가입이 없으므로 여기서 끝난다."""

    def __init__(self, email: str) -> None:
        super().__init__(f"관리자로 등록되지 않은 계정: {email}")
        self.email = email


class InvalidRefreshTokenError(AdminAuthError):
    """refresh token이 없거나, 만료됐거나, 이미 회전(rotate)되어 무효화됐다."""
