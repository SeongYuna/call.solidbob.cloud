# Requirement: J-1
from __future__ import annotations

from abc import ABC, abstractmethod


class CurrentAgentUseCase(ABC):
    """요청에 실린 토큰 → 상담원 ID. 무효하면 None."""

    @abstractmethod
    async def current(self, token: str) -> str | None: ...
