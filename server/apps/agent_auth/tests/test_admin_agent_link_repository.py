# Requirement: J-4, QUA-1
"""실제 PostgreSQL(현재 db/schema.sql)에서 관리자 ↔ `agent` 연결(`decisions/314`).

- `ensure_admin` 은 `role='admin'` 행을 한 번만 만든다 — 목록·이름 찾기(`resolve_or_create`)에는 안 나온다
- `link_agent` 는 비어 있을 때만 채운다 — 이미 있으면 덮어쓰지 않고 그 값을 돌려준다

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio

import pytest

from admin_auth.adapter.outbound.postgres.admin_account_repository import PostgresAdminAccountRepository
from agent_auth.adapter.outbound.postgres.agent_directory_repository import PostgresAgentDirectoryRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory

EMAIL = "it-admin-link@example.com"
NAME = "it-관리자이름"
AGENT_IDS = ("it-admin-link", "it-admin-other")


async def _sql(connect, sql, args=None):
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall() if cur.description else None
        await conn.commit()
    return rows


async def _cleanup(connect):
    await _sql(connect, 'DELETE FROM "admin_account" WHERE "email" = %s', (EMAIL,))
    await _sql(connect, 'DELETE FROM "agent" WHERE "agent_id" = ANY(%s) OR "display_name" = %s', (list(AGENT_IDS), NAME))


@pytest.mark.integration
def test_관리자_행은_한_번만_생기고_상담원_목록과_이름_찾기에_안_나온다(integration_settings):
    connect = build_connection_factory(integration_settings)
    agents = PostgresAgentDirectoryRepository(connect)

    async def scenario():
        await _cleanup(connect)
        try:
            first = await agents.ensure_admin(AGENT_IDS[0], NAME)
            again = await agents.ensure_admin(AGENT_IDS[0], "다른이름")  # 두 번째는 만들지도 바꾸지도 않는다
            assert first.agent_id == again.agent_id == AGENT_IDS[0] and again.display_name == NAME
            (role,) = (await _sql(connect, 'SELECT "role" FROM "agent" WHERE "agent_id" = %s', (AGENT_IDS[0],)))[0]
            assert role == "admin"

            assert AGENT_IDS[0] not in {a.agent_id for a in await agents.list()}
            # 같은 이름으로 토큰을 발급하면 관리자 행을 빌리지 않고 상담원을 새로 만든다
            created = await agents.resolve_or_create(NAME)
            assert created.agent_id != AGENT_IDS[0]
        finally:
            await _cleanup(connect)

    asyncio.run(scenario())


@pytest.mark.integration
def test_link_agent_는_비어_있을_때만_채운다(integration_settings):
    connect = build_connection_factory(integration_settings)
    agents = PostgresAgentDirectoryRepository(connect)
    admins = PostgresAdminAccountRepository(connect)

    async def scenario():
        await _cleanup(connect)
        try:
            for agent_id in AGENT_IDS:
                await agents.ensure_admin(agent_id, agent_id)
            (account_id,) = (await _sql(
                connect,
                'INSERT INTO "admin_account" ("email", "name", "created_at") VALUES (%s, %s, now()) RETURNING "id"',
                (EMAIL, NAME),
            ))[0]

            assert await admins.link_agent(account_id, AGENT_IDS[0]) == AGENT_IDS[0]
            assert await admins.link_agent(account_id, AGENT_IDS[1]) == AGENT_IDS[0]  # 덮어쓰지 않는다
            assert (await admins.find_by_id(account_id)).agent_id == AGENT_IDS[0]
        finally:
            await _cleanup(connect)

    asyncio.run(scenario())


@pytest.mark.integration
def test_관리자_행과_같은_ID로_발급하면_500이_아니라_UnknownAgentError다(integration_settings):
    """INSERT 가 `ON CONFLICT DO NOTHING` 이라 PK 위반(500) 대신 다시 찾는다 — 관리자 행은 빌려주지 않는다."""
    from agent_auth.app.dtos.agent_token_dto import UnknownAgentError

    connect = build_connection_factory(integration_settings)
    agents = PostgresAgentDirectoryRepository(connect)

    async def scenario():
        await _cleanup(connect)
        try:
            await agents.ensure_admin(AGENT_IDS[0], NAME)
            with pytest.raises(UnknownAgentError):
                await agents.resolve_or_create(AGENT_IDS[0])
        finally:
            await _cleanup(connect)

    asyncio.run(scenario())
