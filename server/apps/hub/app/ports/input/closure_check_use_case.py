# Requirement: F-2
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.closure_dto import ClosureCheckCommand
from hub.app.dtos.closure_verdict_dto import ClosureVerdict


class ClosureCheckUseCase(ABC):
    """F-2 필요서류 체크리스트 — 호출자가 서류별 안내 여부를 채운다. **빠진 서류는 하나도 빠짐없이 `missing` 에** — 절대 규칙.

    평균·부분 점수가 없다. 1건이라도 어긋나면 실패로 처리한다([6.2절](/docs/06/)). 판정은 규칙이 한다(절대 원칙 9).
    """

    @abstractmethod
    async def check(self, command: ClosureCheckCommand) -> ClosureVerdict: ...
