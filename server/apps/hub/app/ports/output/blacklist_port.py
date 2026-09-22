# Requirement: J-2, J-4, J-5
from __future__ import annotations

from abc import ABC, abstractmethod

from datetime import datetime

from hub.app.dtos.blacklist_dto import BlacklistEntry, BlacklistRequest, ExpiryChange
from hub.app.dtos.blacklist_retention_dto import RetentionPurgeResult


class BlacklistNotFound(LookupError):
    """요청·등록 번호가 없다."""


class UnknownAgent(ValueError):
    """`requested_by` 가 상담원 마스터(`agent`)에 없다."""


class BlacklistConflict(ValueError):
    """상태가 맞지 않는다 — 이미 결정된 요청 · 이미 적용 중인 등록이 있는 고객 · 이미 해제된 등록."""


class ExpiryBeyondCap(ValueError):
    """새 만료가 누적 상한(승인일 + 365일)을 넘는다(`decisions/309` 추가). 상태 충돌이 아니라 입력이 정책을 넘은 것이라 409 가 아니다."""

    def __init__(self, latest_allowed: datetime) -> None:
        super().__init__(f"연장 누적 상한을 넘습니다 — 이 등록은 {latest_allowed.isoformat()} 까지만 둘 수 있습니다. 더 두려면 새 요청으로 재등록합니다")
        self.latest_allowed = latest_allowed


class BlacklistPort(ABC):
    """블랙리스트 요청·등록의 저장과 조회. 근거: `_project/decisions/204`.

    **상태 전이 규칙은 이 포트가 갖지 않는다** — 규칙은 도메인(`blacklist/domain/`)에
    있고 여기는 저장소다. 어댑터가 상태를 마음대로 바꿀 수 있으면 「승인 없이 active」가
    저장소 구현마다 가능해진다.
    """

    @abstractmethod
    async def save_request(self, request: BlacklistRequest) -> BlacklistRequest:
        """전환 요청을 남기고 DB 가 채운 번호·시각까지 담아 돌려준다. 항상 `pending` 으로 들어간다.
        요청자가 상담원 마스터에 없으면 `UnknownAgent`."""

    @abstractmethod
    async def list_requests(self, status: str | None = None, requested_by: str | None = None) -> list[BlacklistRequest]:
        """관리자 승인요청창이 읽는 목록. `requested_by` 를 주면 그 상담원이 올린 것만 — 「내 요청」(`w6-agent-my-requests-api`)."""

    @abstractmethod
    async def decide(
        self, request_id: str, *, approve: bool, decided_by: str, expires_at: datetime | None, note: str | None
    ) -> BlacklistRequest:
        """관리자 판단을 반영한다. 승인이면 등록까지 이어진다(`expires_at` 필수).

        상태 전이는 구현체가 도메인 규칙(`blacklist.domain.services.transitions`)으로 확인한다 —
        어긋나면 `BlacklistConflict`, 없으면 `BlacklistNotFound`."""

    @abstractmethod
    async def find_entry(self, customer_ref: str) -> BlacklistEntry | None:
        """인입 시 배정(J-5)이 부른다. 없으면 None."""

    @abstractmethod
    async def list_entries(self, active_only: bool = False) -> list[BlacklistEntry]:
        """관리자 블랙리스트 관리창이 읽는 목록. 해제·만료된 에피소드도 남아 있다(재범 판단 근거)."""

    @abstractmethod
    async def release_entry(self, entry_id: int, *, released_by: str, reason: str) -> BlacklistEntry:
        """등록을 해제한다. **행을 지우지 않는다** — 왜 풀렸는지가 남아야 한다(`decisions/205`)."""

    @abstractmethod
    async def change_expiry(
        self, entry_id: int, *, changed_by: str, expires_at: datetime, reason: str
    ) -> tuple[BlacklistEntry, ExpiryChange]:
        """등록의 만료 시각을 바꾸고 변경 1건을 쌓는다(`decisions/309`). 연장·단축 모두.
        없으면 `BlacklistNotFound`, 이미 해제된 등록이면 `BlacklistConflict`, 승인일 + 365일을 넘으면 `ExpiryBeyondCap`."""

    @abstractmethod
    async def list_expiry_changes(self, entry_id: int) -> list[ExpiryChange]:
        """만료 변경 이력, 오래된 순. 등록이 없으면 `BlacklistNotFound`."""

    @abstractmethod
    async def purge_retained_texts(self) -> RetentionPurgeResult:
        """보존 기간이 지난 자유 입력 문장을 표시로 바꾼다(`decisions/312`). 행을 지우지 않는다. 여러 번 불러도 결과가 같다."""
