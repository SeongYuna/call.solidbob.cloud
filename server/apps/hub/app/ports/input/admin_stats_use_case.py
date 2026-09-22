# Requirement: J-3, J-5, C-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.admin_stats_dto import AdminStats


class AdminStatsUseCase(ABC):
    """`GET /hub/admin-stats` — 관리자 현황판의 숫자를 한 번에 준다."""

    @abstractmethod
    async def get(self) -> AdminStats: ...
