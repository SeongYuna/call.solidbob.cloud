# Requirement: J-1, SEC-1, QUA-1
"""실제 PostgreSQL(현재 db/schema.sql)에서: 해시만 저장 · 폐기 후 조회 안 됨 · 없는 상담원은 UnknownAgentError.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio

import pytest

from agent_auth.adapter.outbound.postgres.agent_token_repository import PostgresAgentTokenRepository
from agent_auth.app.dtos.agent_token_dto import UnknownAgentError
from agent_auth.domain.services.agent_token import hash_token, new_token
from hub.adapter.outbound.postgres.connection import build_connection_factory

AGENT = "it-agent-token"


async def _sql(connect, sql, args=None):
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall() if cur.description else None
        await conn.commit()
    return rows


@pytest.mark.integration
def test_실제_DB에_해시만_남고_폐기하면_상담원을_못_찾는다(integration_settings):
    connect = build_connection_factory(integration_settings)
    repo = PostgresAgentTokenRepository(connect)
    token = new_token()

    async def scenario():
        await _sql(connect, 'DELETE FROM "agent_token" WHERE "agent_id" = %s', (AGENT,))
        await _sql(connect, 'DELETE FROM "agent" WHERE "agent_id" = %s', (AGENT,))
        await _sql(connect, 'INSERT INTO "agent" ("agent_id", "display_name", "role") VALUES (%s, %s, %s)',
                   (AGENT, "통합테스트", "agent"))
        try:
            item = await repo.save(AGENT, hash_token(token), None)
            stored = await _sql(connect, 'SELECT "token_hash" FROM "agent_token" WHERE "id" = %s', (item.id,))
            assert stored == [(hash_token(token),)]
            dump = await _sql(connect, 'SELECT * FROM "agent_token" WHERE "agent_id" = %s', (AGENT,))
            assert token not in str(dump)  # 원문은 어느 컬럼에도 없다

            assert await repo.find_active_agent_id(hash_token(token)) == AGENT
            assert [t.id for t in await repo.list(AGENT)] == [item.id]

            first = await repo.revoke(item.id)
            again = await repo.revoke(item.id)
            assert first.revoked_at is not None and again.revoked_at == first.revoked_at  # 처음 시각 유지
            assert await repo.find_active_agent_id(hash_token(token)) is None
            assert await repo.revoke(-1) is None

            with pytest.raises(UnknownAgentError):
                await repo.save("it-nobody", hash_token(new_token()), None)
        finally:
            await _sql(connect, 'DELETE FROM "agent_token" WHERE "agent_id" = %s', (AGENT,))
            await _sql(connect, 'DELETE FROM "agent" WHERE "agent_id" = %s', (AGENT,))

    asyncio.run(scenario())
