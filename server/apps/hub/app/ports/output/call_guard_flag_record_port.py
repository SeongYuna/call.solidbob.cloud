# Requirement: C-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_guard_dto import CallGuardFlag


class CallGuardFlagSpanMissingError(RuntimeError):
    """위치(span) 없는 신호가 저장소까지 왔다 — **요청이 아니라 스포크 구현이 틀린 것**이다.

    저장 실패를 삼키는 인터랙터도 이것은 삼키지 않는다(2026-09-20). 「DB 가 잠깐 안 된다」와 달리
    기다려도 낫지 않고, 조용히 넘기면 탐지 기록이 통째로 안 남는 결함이 로그 한 줄 뒤에 숨는다.
    """


class CallGuardFlagRecordPort(ABC):
    """잡힌 콜 가드 신호를 남긴다. append-only — 통화가 끝나면 다시 계산할 오디오·원문이 없다.

    `flags` 의 `phrase`·`span` 은 **마스킹된 발화 기준**이어야 한다(MANUAL-5.5). 원문을 받는 시그니처를 두지 않는다.
    """

    @abstractmethod
    async def record(self, call_id: str, segment_id: int, flags: tuple[CallGuardFlag, ...]) -> None: ...
