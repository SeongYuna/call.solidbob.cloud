# Requirement: J-1, SEC-1
"""AgentTokenPort 의 PostgreSQL 구현. **해시만 다룬다** — 원문 토큰을 받는 메서드가 없다."""

from __future__ import annotations

from datetime import datetime, timezone

from agent_auth.app.dtos.agent_token_dto import AgentTokenItem, UnknownAgentError
from agent_auth.app.ports.output.agent_token_port import AgentTokenPort
from hub.adapter.outbound.postgres.connection import ConnectionFactory

_FOREIGN_KEY_VIOLATION = "23503"  # psycopg 를 import 하지 않고 SQLSTATE 로 가린다(connection.py 주석)

_COLUMNS = '"id", "agent_id", "issued_by", "issued_at", "revoked_at"'

_INSERT = f"""
INSERT INTO "agent_token" ("agent_id", "token_hash", "issued_by", "issued_at")
VALUES (%s, %s, %s, %s)
RETURNING {_COLUMNS}
"""
_SELECT_ACTIVE = 'SELECT "agent_id" FROM "agent_token" WHERE "token_hash" = %s AND "revoked_at" IS NULL'
_LIST_ALL = f'SELECT {_COLUMNS} FROM "agent_token" ORDER BY "issued_at" DESC, "id" DESC'
_LIST_BY_AGENT = f'SELECT {_COLUMNS} FROM "agent_token" WHERE "agent_id" = %s ORDER BY "issued_at" DESC, "id" DESC'
# 이미 폐기된 토큰은 처음 폐기 시각을 지킨다 — 두 번 눌러도 흔적이 덮이지 않는다
_REVOKE = f"""
UPDATE "agent_token" SET "revoked_at" = COALESCE("revoked_at", %s) WHERE "id" = %s
RETURNING {_COLUMNS}
"""


def _item(row) -> AgentTokenItem:
    token_id, agent_id, issued_by, issued_at, revoked_at = row
    return AgentTokenItem(id=token_id, agent_id=agent_id, issued_by=issued_by, issued_at=issued_at, revoked_at=revoked_at)


class PostgresAgentTokenRepository(AgentTokenPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def save(self, agent_id: str, token_hash: str, issued_by: int) -> AgentTokenItem:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(_INSERT, (agent_id, token_hash, issued_by, datetime.now(timezone.utc)))
                except Exception as exc:
                    if getattr(exc, "sqlstate", None) == _FOREIGN_KEY_VIOLATION:
                        raise UnknownAgentError(f"상담원이 없습니다: {agent_id}") from exc
                    raise
                row = await cur.fetchone()
            await conn.commit()
        return _item(row)

    async def find_active_agent_id(self, token_hash: str) -> str | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_SELECT_ACTIVE, (token_hash,))
                row = await cur.fetchone()
        return row[0] if row else None

    async def list(self, agent_id: str | None) -> list[AgentTokenItem]:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                if agent_id is None:
                    await cur.execute(_LIST_ALL)
                else:
                    await cur.execute(_LIST_BY_AGENT, (agent_id,))
                rows = await cur.fetchall()
        return [_item(r) for r in rows]

    async def revoke(self, token_id: int) -> AgentTokenItem | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_REVOKE, (datetime.now(timezone.utc), token_id))
                row = await cur.fetchone()
            await conn.commit()
        return _item(row) if row else None
