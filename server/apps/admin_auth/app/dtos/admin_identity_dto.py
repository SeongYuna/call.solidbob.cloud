# Requirement: 관리자 로그인(구글)
"""구글이 검증해 준 신원과, 저장소에 있는 관리자 계정."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoogleIdentity:
    """구글 id_token 검증 결과 — 아직 관리자인지는 모른다."""

    email: str
    name: str | None


@dataclass(frozen=True)
class AdminAccount:
    """`admin_account` 행. 회원가입이 없으므로 이 행이 있어야만 관리자다."""

    id: int
    email: str
    name: str | None
    # J-4 승인·해제를 기록할 상담원 마스터 ID(`decisions/304`). None 이면 블랙리스트 결정을 못 한다
    agent_id: str | None = None
