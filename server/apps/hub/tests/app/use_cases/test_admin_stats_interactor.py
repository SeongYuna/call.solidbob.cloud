# Requirement: J-3, QUA-1
import asyncio
from datetime import datetime, timezone

from hub.app.dtos.admin_stats_dto import AdminStats
from hub.app.ports.output.admin_stats_port import AdminStatsPort
from hub.app.use_cases.admin_stats_interactor import AdminStatsInteractor

STATS = AdminStats(5, 3, 2, 1, 1, 4, 2, 1, counted_at=datetime(2026, 9, 22, tzinfo=timezone.utc))


class _Port(AdminStatsPort):
    async def count(self):
        return STATS


def test_센_값을_그대로_넘긴다():
    assert asyncio.run(AdminStatsInteractor(_Port()).get()) == STATS


def test_상담원_단위_필드가_없다():
    """부록 A-1 — 누가 몇 건을 했는지는 이 API 로 알 수 없다."""
    assert not any("agent" in name for name in AdminStats.__dataclass_fields__)
