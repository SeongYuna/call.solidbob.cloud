# Requirement: J-5
"""RoutingSettingPort 의 PostgreSQL 구현 — `app_setting` 의 `veteran_years` 한 줄(`decisions/313`).

저장값이 없으면 **도메인 기본값**(`routing.DEFAULT_VETERAN_YEARS`)을 `saved=False` 로 돌려준다 — 기본값을 두 곳에 적지 않는다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hub.adapter.outbound.postgres.connection import ConnectionFactory
from hub.app.dtos.routing_setting_dto import RoutingSetting
from hub.app.ports.output.routing_setting_port import RoutingSettingPort

from ...domain.services.routing import DEFAULT_VETERAN_YEARS

VETERAN_YEARS_KEY = "veteran_years"

_SELECT = 'SELECT "value", "updated_at", "updated_by" FROM "app_setting" WHERE "setting_key" = %s'
_UPSERT = """
INSERT INTO "app_setting" ("setting_key", "value", "updated_at", "updated_by") VALUES (%s, %s, %s, %s)
ON CONFLICT ("setting_key") DO UPDATE SET "value" = EXCLUDED."value", "updated_at" = EXCLUDED."updated_at", "updated_by" = EXCLUDED."updated_by"
RETURNING "value", "updated_at", "updated_by"
"""


def _setting(row) -> RoutingSetting:
    if row is None:
        return RoutingSetting(veteran_years=DEFAULT_VETERAN_YEARS, saved=False)
    value, updated_at, updated_by = row
    return RoutingSetting(veteran_years=float(value), saved=True, updated_at=updated_at, updated_by=updated_by)


async def read_veteran_years(cur) -> float:
    """같은 커넥션 안에서 기준만 읽는다 — 배정 어댑터가 판정과 한 트랜잭션에서 쓴다."""
    await cur.execute(_SELECT, (VETERAN_YEARS_KEY,))
    return _setting(await cur.fetchone()).veteran_years


class PostgresRoutingSettingRepository(RoutingSettingPort):
    def __init__(self, connect: ConnectionFactory, now=lambda: datetime.now(timezone.utc)) -> None:
        self._connect = connect
        self._now = now

    async def get(self) -> RoutingSetting:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_SELECT, (VETERAN_YEARS_KEY,))
                row = await cur.fetchone()
        return _setting(row)

    async def save(self, veteran_years: float, updated_by: int) -> RoutingSetting:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_UPSERT, (VETERAN_YEARS_KEY, repr(float(veteran_years)), self._now(), updated_by))
                row = await cur.fetchone()
            await conn.commit()
        return _setting(row)
