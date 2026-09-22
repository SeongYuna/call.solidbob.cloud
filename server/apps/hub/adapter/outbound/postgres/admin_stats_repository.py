# Requirement: J-3, J-5, C-6
"""AdminStatsPort 의 PostgreSQL 구현 — 문장 하나로 센다(같은 스냅샷). 상담원 컬럼으로 묶지 않는다(부록 A-1).

「적용 중 등록」은 블랙리스트 저장소의 `_ACTIVE` 와 같은 조건이다 — 해제되지 않았고 만료 전.
"""

from __future__ import annotations

from hub.app.dtos.admin_stats_dto import AdminStats
from hub.app.ports.output.admin_stats_port import AdminStatsPort

from .connection import ConnectionFactory

_COUNT = """
SELECT
    (SELECT COUNT(*) FROM "call"),
    (SELECT COUNT(*) FROM "call" WHERE "status" = 'closed'),
    (SELECT COUNT(*) FROM "call_guard_flag"),
    (SELECT COUNT(*) FROM "blacklist_request" WHERE "status" = 'pending'),
    (SELECT COUNT(*) FROM "blacklist_entry" WHERE "released_at" IS NULL AND "expires_at" > NOW()),
    (SELECT COUNT(*) FROM "routing_log"),
    (SELECT COUNT(*) FROM "routing_log" WHERE "is_blacklisted"),
    (SELECT COUNT(*) FROM "routing_log" WHERE "fell_back"),
    NOW()
"""


class PostgresAdminStatsRepository(AdminStatsPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def count(self) -> AdminStats:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_COUNT)
                row = await cur.fetchone()
        return AdminStats(*(int(v) for v in row[:8]), counted_at=row[8])
