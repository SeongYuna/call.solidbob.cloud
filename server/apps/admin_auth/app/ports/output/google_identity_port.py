# Requirement: 관리자 로그인(구글)
from __future__ import annotations

from abc import ABC, abstractmethod

from admin_auth.app.dtos.admin_identity_dto import GoogleIdentity


class GoogleIdentityPort(ABC):
    """구글이 발급한 id_token을 검증한다. 서명·issuer·audience·만료를 전부 확인하는 것은
    구현체(Google 공식 라이브러리) 책임이고, 여기는 계약만 정의한다."""

    @abstractmethod
    async def verify(self, id_token: str) -> GoogleIdentity:
        """검증 실패 시 InvalidGoogleTokenError를 던진다."""
        ...
