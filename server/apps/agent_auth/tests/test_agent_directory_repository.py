# Requirement: J-1, QUA-1
"""실제 PostgreSQL(현재 db/schema.sql)에서: 이름으로 찾고, 없으면 그 자리에서 만든다(`decisions/406`).
agent_id 는 이름 그대로 쓴다 — VARCHAR(20)을 넘는 이름만 무작위값으로 대신한다.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio

import pytest

from agent_auth.adapter.outbound.postgres.agent_directory_repository import PostgresAgentDirectoryRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory

NAME = "it-처음보는이름"
LONG_NAME = "it-이십자를훌쩍넘는아주아주아주긴이름입니다"  # 20자 초과


async def _sql(connect, sql, args=None):
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall() if cur.description else None
        await conn.commit()
    return rows


@pytest.mark.integration
def test_실제_DB에서_이름으로_찾고_없으면_agent_id로_그대로_만든다(integration_settings):
    connect = build_connection_factory(integration_settings)
    repo = PostgresAgentDirectoryRepository(connect)

    async def scenario():
        await _sql(connect, 'DELETE FROM "agent" WHERE "display_name" = %s', (NAME,))
        try:
            created = await repo.resolve_or_create(NAME)
            assert created.display_name == NAME
            assert created.agent_id == NAME  # agent_id 는 이름 그대로 쓴다

            again_by_name = await repo.resolve_or_create(NAME)
            assert again_by_name.agent_id == created.agent_id  # 두 번째는 새로 안 만든다

            again_by_id = await repo.resolve_or_create(created.agent_id)
            assert again_by_id.agent_id == created.agent_id
        finally:
            await _sql(connect, 'DELETE FROM "agent" WHERE "display_name" = %s', (NAME,))

    asyncio.run(scenario())


@pytest.mark.integration
def test_20자_넘는_이름은_무작위_agent_id로_만든다(integration_settings):
    connect = build_connection_factory(integration_settings)
    repo = PostgresAgentDirectoryRepository(connect)
    assert len(LONG_NAME) > 20

    async def scenario():
        await _sql(connect, 'DELETE FROM "agent" WHERE "display_name" = %s', (LONG_NAME,))
        try:
            created = await repo.resolve_or_create(LONG_NAME)
            assert created.display_name == LONG_NAME
            assert created.agent_id != LONG_NAME
            assert len(created.agent_id) <= 20
        finally:
            await _sql(connect, 'DELETE FROM "agent" WHERE "display_name" = %s', (LONG_NAME,))

    asyncio.run(scenario())


@pytest.mark.integration
def test_실제_DB에서_입사일을_넣고_지운다_관리자_행은_건드리지_않는다(integration_settings):
    """J-5 근속은 `agent.hired_on` 에서 센다(`decisions/321`) — 넣는 길이 없어서 모두 0년이었다."""
    from datetime import date  # noqa: PLC0415

    connect = build_connection_factory(integration_settings)
    repo = PostgresAgentDirectoryRepository(connect)
    admin_id = "admin-it-hired"

    async def scenario():
        await _sql(connect, 'DELETE FROM "agent" WHERE "display_name" = %s OR "agent_id" = %s', (NAME, admin_id))
        try:
            created = await repo.resolve_or_create(NAME)
            saved = await repo.set_hired_on(created.agent_id, date(2019, 3, 2))
            assert saved is not None and saved.hired_on == date(2019, 3, 2)
            listed = {a.agent_id: a.hired_on for a in await repo.list()}
            assert listed[created.agent_id] == date(2019, 3, 2)

            cleared = await repo.set_hired_on(created.agent_id, None)
            assert cleared is not None and cleared.hired_on is None

            assert await repo.set_hired_on("it-없는상담원", date(2019, 3, 2)) is None
            await repo.ensure_admin(admin_id, "관리자")
            assert await repo.set_hired_on(admin_id, date(2019, 3, 2)) is None  # 관리자 행은 배정 후보가 아니다
        finally:
            await _sql(connect, 'DELETE FROM "agent" WHERE "display_name" = %s OR "agent_id" = %s', (NAME, admin_id))

    asyncio.run(scenario())
