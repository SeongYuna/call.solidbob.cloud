# Requirement: 관리자 로그인(구글)
"""다른 관리자 전용 라우터가 재사용할 수 있는 인증 가드. `Authorization: Bearer <access_token>`을
읽어 현재 관리자를 돌려준다 — 없거나 무효하면 401.

**헤더 검사를 의존성보다 먼저 한다 (2026-09-15).** 전에는 헤더를 보기 전에 `CurrentAdminUseCase` →
Redis 프로바이더를 먼저 풀어서, Redis 가 없는 운영에서는 **헤더 없는 요청도 401 이 아니라 500** 이었다
(`0.1.8` 배포 확인). FastAPI 는 하위 의존성을 선언 순서대로 푼다 — `bearer_token` 을 앞에 둬
헤더가 없으면 인프라를 타기 전에 401 로 끝낸다."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.ports.input.current_admin_use_case import CurrentAdminUseCase
from admin_auth.dependencies.use_case_providers import get_current_admin_use_case


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    return authorization.split(" ", 1)[1].strip()


async def require_admin(
    token: str = Depends(bearer_token),  # ⚠ 순서가 계약이다 — use_case 보다 앞에 둔다
    use_case: CurrentAdminUseCase = Depends(get_current_admin_use_case),
) -> AdminAccount:
    account = await use_case.current(token)
    if account is None:
        raise HTTPException(status_code=401, detail="세션이 없거나 만료됐습니다 — 다시 로그인해 주세요")
    return account
