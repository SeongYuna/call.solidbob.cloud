# Requirement: 관리자 로그인(구글)
from __future__ import annotations

from abc import ABC, abstractmethod


class LogoutUseCase(ABC):
    """현재 access token 세션과 refresh token을 모두 무효화한다. 이미 무효한 값이 와도 조용히 끝난다
    (로그아웃은 멱등이어야 한다 — 두 번 눌러도 에러가 아니다)."""

    @abstractmethod
    async def logout(self, access_token: str | None, refresh_token: str | None) -> None: ...
