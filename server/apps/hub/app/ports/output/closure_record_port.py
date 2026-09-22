# Requirement: F-2
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.closure_verdict_dto import ClosureVerdict


class ClosureRecordPort(ABC):
    """판정을 append 한다(`closure` + `closure_item`). 갱신하지 않는다 — 같은 절차를 다시 판정하면 행이 하나 더 생긴다.
    통화(`call`)가 없으면 `CallNotStartedError`."""

    @abstractmethod
    async def record(self, verdict: ClosureVerdict) -> None: ...
