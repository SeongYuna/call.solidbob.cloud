# Requirement: C-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_guard_dto import CallGuardFlag


class CallGuardFlagRecordPort(ABC):
    """잡힌 콜 가드 신호를 남긴다. append-only — 통화가 끝나면 다시 계산할 오디오·원문이 없다.

    `flags` 의 `phrase`·`span` 은 **마스킹된 발화 기준**이어야 한다(MANUAL-5.5). 원문을 받는 시그니처를 두지 않는다.
    """

    @abstractmethod
    async def record(self, call_id: str, segment_id: int, flags: tuple[CallGuardFlag, ...]) -> None: ...
