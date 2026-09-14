# Requirement: 관리자 로그인(구글)
"""다른 관리자 전용 라우터가 재사용할 수 있는 인증 가드. `Authorization: Bearer <access_token>`을
읽어 현재 관리자를 돌려준다 — 없거나 무효하면 401."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.ports.input.current_admin_use_case import CurrentAdminUseCase
from admin_auth.dependencies.use_case_providers import get_current_admin_use_case


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization: Bearer <access_token> 헤더가 필요하다")
    return authorization.split(" ", 1)[1].strip()


async def require_admin(
    authorization: str | None = Header(default=None),
    use_case: CurrentAdminUseCase = Depends(get_current_admin_use_case),
) -> AdminAccount:
    token = _bearer_token(authorization)
    account = await use_case.current(token)
    if account is None:
        raise HTTPException(status_code=401, detail="세션이 없거나 만료됐다 — 다시 로그인하거나 refresh 하라")
    return account
