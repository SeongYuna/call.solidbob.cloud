# Requirement: 관리자 로그인(구글)
"""POST /admin/auth/google · /refresh · /logout · GET /admin/auth/me.

회원가입 라우트가 없다 — admin_account 행이 없으면 구글 인증을 통과해도 403이다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.adapter.inbound.api.schemas.auth_schema import (
    AdminMeResponse,
    GoogleLoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPairResponse,
)
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.dtos.errors import InvalidGoogleTokenError, InvalidRefreshTokenError, NotAnAdminError
from admin_auth.app.dtos.token_pair_dto import IssuedTokenPair
from admin_auth.app.ports.input.google_login_use_case import GoogleLoginUseCase
from admin_auth.app.ports.input.logout_use_case import LogoutUseCase
from admin_auth.app.ports.input.refresh_use_case import RefreshUseCase
from admin_auth.dependencies.use_case_providers import (
    get_google_login_use_case,
    get_logout_use_case,
    get_refresh_use_case,
)

auth_router = APIRouter(prefix="/admin/auth", tags=["admin_auth"])


def _to_response(pair: IssuedTokenPair) -> TokenPairResponse:
    return TokenPairResponse(
        access_token=pair.access_token,
        access_token_expires_in=pair.access_token_expires_in,
        refresh_token=pair.refresh_token,
        refresh_token_expires_in=pair.refresh_token_expires_in,
    )


@auth_router.post("/google", response_model=TokenPairResponse)
async def login_with_google(
    body: GoogleLoginRequest,
    use_case: GoogleLoginUseCase = Depends(get_google_login_use_case),
) -> TokenPairResponse:
    try:
        pair = await use_case.login(body.id_token)
    except InvalidGoogleTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except NotAnAdminError as exc:
        raise HTTPException(status_code=403, detail="관리자로 등록되지 않은 계정이다") from exc
    return _to_response(pair)


@auth_router.post("/refresh", response_model=TokenPairResponse)
async def refresh_tokens(
    body: RefreshRequest,
    use_case: RefreshUseCase = Depends(get_refresh_use_case),
) -> TokenPairResponse:
    try:
        pair = await use_case.refresh(body.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(status_code=401, detail="refresh token이 없거나 만료됐다 — 다시 로그인하라") from exc
    return _to_response(pair)


@auth_router.post("/logout", status_code=204)
async def logout(
    body: LogoutRequest,
    authorization: str | None = Header(default=None),
    use_case: LogoutUseCase = Depends(get_logout_use_case),
) -> None:
    access_token = None
    if authorization and authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1].strip()
    await use_case.logout(access_token, body.refresh_token)


@auth_router.get("/me", response_model=AdminMeResponse)
async def me(admin: AdminAccount = Depends(require_admin)) -> AdminMeResponse:
    return AdminMeResponse(email=admin.email, name=admin.name)

