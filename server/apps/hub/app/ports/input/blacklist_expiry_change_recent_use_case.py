# Requirement: J-4
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_dto import ExpiryChange


class BlacklistRecentExpiryChangeUseCase(ABC):
    """등록을 가리지 않는 최근 만료 변경 — **관리자 감사 로그**가 읽는다(수동 QA Q-67).

    등록별 이력(`BlacklistExpiryChangeListUseCase`)과 나눠 둔다. 하나는 「이 등록이 어떻게
    바뀌어 왔나」, 이것은 「지금까지 누가 무엇을 바꿨나」다 — 감사 로그가 등록마다 물으면 N+1 이다.
    """

    @abstractmethod
    async def recent(self, limit: int) -> list[ExpiryChange]: ...
