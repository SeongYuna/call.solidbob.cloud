# Requirement: J-3, J-5, C-6
"""현황판 인터랙터 — 판정 없음. 포트가 센 값을 그대로 넘긴다."""

from __future__ import annotations

from hub.app.dtos.admin_stats_dto import AdminStats
from hub.app.ports.input.admin_stats_use_case import AdminStatsUseCase
from hub.app.ports.output.admin_stats_port import AdminStatsPort


class AdminStatsInteractor(AdminStatsUseCase):
    def __init__(self, stats: AdminStatsPort) -> None:
        self._stats = stats

    async def get(self) -> AdminStats:
        return await self._stats.count()
