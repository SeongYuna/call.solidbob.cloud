# Requirement: J-3, J-5, C-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.admin_stats_dto import AdminStats


class AdminStatsPort(ABC):
    """저장된 사실을 센다. 한 번의 조회로 같은 시점의 값을 준다 — 칸마다 다른 시각이 섞이지 않게."""

    @abstractmethod
    async def count(self) -> AdminStats: ...
