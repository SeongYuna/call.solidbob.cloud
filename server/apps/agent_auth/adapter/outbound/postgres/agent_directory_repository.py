# Requirement: J-1
"""AgentDirectoryPort 의 PostgreSQL 구현. `agent` 테이블을 이름순으로 그대로 읽는다 — 판정 없음."""

from __future__ import annotations

import secrets
from datetime import date

from agent_auth.app.dtos.agent_directory_dto import AgentSummary
from agent_auth.app.dtos.agent_token_dto import UnknownAgentError
from agent_auth.app.ports.output.agent_directory_port import AgentDirectoryPort
from hub.adapter.outbound.postgres.connection import ConnectionFactory

# 목록·이름 찾기는 상담원(`role='agent'`)만 본다 — 관리자에게 붙은 행(`decisions/314`)이 토큰 발급 후보로 섞이지 않게
_LIST = 'SELECT "agent_id", "display_name", "hired_on" FROM "agent" WHERE "role" = \'agent\' ORDER BY "display_name"'
_GET = 'SELECT "agent_id", "display_name" FROM "agent" WHERE "agent_id" = %s'
_FIND = """
SELECT "agent_id", "display_name" FROM "agent"
WHERE "role" = 'agent' AND ("agent_id" = %s OR "display_name" = %s)
"""
_INSERT = """
INSERT INTO "agent" ("agent_id", "display_name", "role")
VALUES (%s, %s, 'agent')
ON CONFLICT ("agent_id") DO NOTHING
RETURNING "agent_id", "display_name"
"""
# 상담원만 — 관리자 행은 배정 후보가 아니다(`decisions/314`). 없으면 행이 안 돌아온다 → 404
_SET_HIRED_ON = """
UPDATE "agent" SET "hired_on" = %s WHERE "agent_id" = %s AND "role" = 'agent'
RETURNING "agent_id", "display_name", "hired_on"
"""
# 같은 관리자가 동시에 두 번 눌러도 행은 하나 — 충돌이면 넣지 않고 아래 _GET 으로 읽는다
_INSERT_ADMIN = """
INSERT INTO "agent" ("agent_id", "display_name", "role")
VALUES (%s, %s, 'admin')
ON CONFLICT ("agent_id") DO NOTHING
"""


class PostgresAgentDirectoryRepository(AgentDirectoryPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def list(self) -> list[AgentSummary]:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LIST)
                rows = await cur.fetchall()
        return [AgentSummary(agent_id=r[0], display_name=r[1], hired_on=r[2]) for r in rows]

    async def get(self, agent_id: str) -> AgentSummary | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_GET, (agent_id,))
                row = await cur.fetchone()
        return AgentSummary(agent_id=row[0], display_name=row[1]) if row is not None else None

    async def set_hired_on(self, agent_id: str, hired_on: date | None) -> AgentSummary | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_SET_HIRED_ON, (hired_on, agent_id))
                row = await cur.fetchone()
            await conn.commit()
        return AgentSummary(agent_id=row[0], display_name=row[1], hired_on=row[2]) if row is not None else None

    async def resolve_or_create(self, identifier: str) -> AgentSummary:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_FIND, (identifier, identifier))
                row = await cur.fetchone()
                if row is None:
                    # agent_id 는 이름 그대로 쓴다 — 관리자 화면에 "agent-3f9a…" 같은 임의값이
                    # 아니라 사람이 알아볼 수 있는 값이 남아야 한다. `agent.agent_id`가
                    # VARCHAR(20)이라 이름이 그보다 길 때만(드묾) 무작위값으로 대신한다.
                    new_agent_id = identifier if len(identifier) <= 20 else f"agent-{secrets.token_hex(6)}"
                    await cur.execute(_INSERT, (new_agent_id, identifier))
                    row = await cur.fetchone()
                    await conn.commit()
                    if row is None:
                        # 두 발급이 동시에 같은 이름을 만들었다 — 먼저 넣은 쪽을 쓴다(전엔 PK 위반 500).
                        # 그래도 없으면 그 ID 가 관리자 행(`decisions/314`)이다 — 관리자 행을 상담원으로 빌려주지 않는다
                        await cur.execute(_FIND, (identifier, identifier))
                        row = await cur.fetchone()
                        if row is None:
                            raise UnknownAgentError(identifier)
        return AgentSummary(agent_id=row[0], display_name=row[1])

    async def ensure_admin(self, agent_id: str, display_name: str) -> AgentSummary:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_INSERT_ADMIN, (agent_id, display_name))
                await cur.execute(_GET, (agent_id,))
                row = await cur.fetchone()
            await conn.commit()
        return AgentSummary(agent_id=row[0], display_name=row[1])
