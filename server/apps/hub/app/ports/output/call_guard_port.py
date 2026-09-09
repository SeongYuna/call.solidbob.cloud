# Requirement: C-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_guard_dto import CallGuardFlag


class CallGuardPort(ABC):
    """C-6. **고객** 발화에서 폭언·위기 신호를 찾는다. 재현율 우선 — 애매하면 잡는다.

    `CompliancePort`(C-1~C-4)와 방향이 반대다. 두 포트를 하나로 합치지 않는 이유는
    화자가 다르고 사전이 다르기 때문이다(`_project/decisions/201`).

    ⚠ **판정만 한다.** 통화를 끊을지, 상급자를 부를지는 이 포트가 정하지 않는다 —
    `DASAN-MANUAL-5.2` 가 최종 판단을 상담원과 상급자에게 두고 시스템은 "탐지와 경고까지"
    라고 정한다.

    구현이 규칙 기반이면 동기로 충분하지만, 분류기가 붙을 수 있어 `CompliancePort` 와
    같게 async 로 연다 — 나중에 바꾸면 배선이 전부 깨진다.
    """

    @abstractmethod
    async def detect(self, customer_utterance: str) -> list[CallGuardFlag]: ...
