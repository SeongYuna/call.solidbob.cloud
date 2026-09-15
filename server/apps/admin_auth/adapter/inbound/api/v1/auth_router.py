# Requirement: 관리자 로그인(구글)
"""POST /admin/auth/google · /refresh · /logout · GET /admin/auth/me · GET /admin/auth/test.

회원가입 라우트가 없다 — admin_account 행이 없으면 구글 인증을 통과해도 403이다.

`/test` 는 **배포 확인용 프로브**다(2026-09-15, 정성윤). 인증도 DB 도 Redis 도 타지 않아서,
「코드를 고쳐 머지하면 운영의 `/docs`·`/openapi.json` 이 실제로 바뀌는가」만 본다.
확인이 끝나면 걷어낸다 — [미결 항목](/open-items/)에 그 조건을 적어 두었다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.adapter.inbound.api.schemas.auth_schema import (
    AdminMeResponse,
    AuthProbeResponse,
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


# `PROBE_MARKER` 는 손으로 올린다 — 이미지에 자동으로 박히는 값이 아니다. 새 이미지가 실제로
# 떴는지 보려면 `infra/k8s/base/kustomization.yaml` 의 `newTag` 와 **같은 PR 안에서** 같이 올린다.
# (태그를 안 올리면 `imagePullPolicy: IfNotPresent` 라 노드가 옛 이미지를 계속 쓴다 —
#  `scripts/check_release_tags.py` 가 그 조합을 빨간불로 만든다.)
PROBE_MARKER = "0.1.7"


@auth_router.get(
    "/test",
    response_model=AuthProbeResponse,
    summary="배포 확인용 프로브",
    description="인증·DB·Redis 를 타지 않는다. 머지한 코드가 운영에 실제로 떴는지, "
                "그리고 `/openapi.json` 이 따라 바뀌는지만 확인한다.",
)
async def probe() -> AuthProbeResponse:
    """토큰을 요구하지 않는다 — 요구하면 「배포가 됐는지」와 「로그인이 되는지」가 섞인다.

    비밀을 하나도 싣지 않는다(SEC-2). 설정 여부조차 싣지 않는다 — 그건 `/health` 의 일이다.
    """
    return AuthProbeResponse(status="ok", router="admin_auth", marker=PROBE_MARKER)
