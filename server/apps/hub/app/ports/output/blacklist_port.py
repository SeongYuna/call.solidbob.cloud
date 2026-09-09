# Requirement: J-2, J-4, J-5
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_dto import BlacklistEntry, BlacklistRequest


class BlacklistPort(ABC):
    """블랙리스트 요청·등록의 저장과 조회. 근거: `_project/decisions/204`.

    **상태 전이 규칙은 이 포트가 갖지 않는다** — 규칙은 도메인(`blacklist/domain/`)에
    있고 여기는 저장소다. 어댑터가 상태를 마음대로 바꿀 수 있으면 「승인 없이 active」가
    저장소 구현마다 가능해진다.
    """

    @abstractmethod
    async def save_request(self, request: BlacklistRequest) -> str:
        """전환 요청을 남기고 `request_id` 를 돌려준다. 항상 `pending` 으로 들어간다."""

    @abstractmethod
    async def list_requests(self, status: str | None = None) -> list[BlacklistRequest]:
        """관리자 승인요청창이 읽는 목록."""

    @abstractmethod
    async def decide(self, request_id: str, *, approve: bool, decided_by: str) -> BlacklistRequest:
        """관리자 판단을 반영한다. 승인이면 등록까지 이어진다."""

    @abstractmethod
    async def find_entry(self, customer_ref: str) -> BlacklistEntry | None:
        """인입 시 배정(J-5)이 부른다. 없으면 None."""

    @abstractmethod
    async def list_entries(self) -> list[BlacklistEntry]:
        """관리자 블랙리스트 관리창이 읽는 목록."""
