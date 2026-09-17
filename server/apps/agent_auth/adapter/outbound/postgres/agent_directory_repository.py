# Requirement: J-1
"""AgentDirectoryPort 의 PostgreSQL 구현. `agent` 테이블을 이름순으로 그대로 읽는다 — 판정 없음."""

from __future__ import annotations

from agent_auth.app.dtos.agent_directory_dto import AgentSummary
from agent_auth.app.ports.output.agent_directory_port import AgentDirectoryPort
from hub.adapter.outbound.postgres.connection import ConnectionFactory

_LIST = 'SELECT "agent_id", "display_name" FROM "agent" ORDER BY "display_name"'


class PostgresAgentDirectoryRepository(AgentDirectoryPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def list(self) -> list[AgentSummary]:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LIST)
                rows = await cur.fetchall()
        return [AgentSummary(agent_id=r[0], display_name=r[1]) for r in rows]
