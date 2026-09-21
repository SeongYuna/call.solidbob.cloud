# Requirement: J-1
"""AgentDirectoryPort 의 PostgreSQL 구현. `agent` 테이블을 이름순으로 그대로 읽는다 — 판정 없음."""

from __future__ import annotations

import secrets

from agent_auth.app.dtos.agent_directory_dto import AgentSummary
from agent_auth.app.ports.output.agent_directory_port import AgentDirectoryPort
from hub.adapter.outbound.postgres.connection import ConnectionFactory

_LIST = 'SELECT "agent_id", "display_name" FROM "agent" ORDER BY "display_name"'
_FIND = 'SELECT "agent_id", "display_name" FROM "agent" WHERE "agent_id" = %s OR "display_name" = %s'
_INSERT = """
INSERT INTO "agent" ("agent_id", "display_name", "role")
VALUES (%s, %s, 'agent')
RETURNING "agent_id", "display_name"
"""


class PostgresAgentDirectoryRepository(AgentDirectoryPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def list(self) -> list[AgentSummary]:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LIST)
                rows = await cur.fetchall()
        return [AgentSummary(agent_id=r[0], display_name=r[1]) for r in rows]

    async def resolve_or_create(self, identifier: str) -> AgentSummary:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_FIND, (identifier, identifier))
                row = await cur.fetchone()
                if row is None:
                    new_agent_id = f"agent-{secrets.token_hex(6)}"
                    await cur.execute(_INSERT, (new_agent_id, identifier))
                    row = await cur.fetchone()
                    await conn.commit()
        return AgentSummary(agent_id=row[0], display_name=row[1])
