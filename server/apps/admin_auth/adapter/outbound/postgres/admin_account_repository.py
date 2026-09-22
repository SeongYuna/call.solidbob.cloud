# Requirement: 관리자 로그인(구글)
"""AdminAccountPort의 PostgreSQL 구현 — `admin_account` 허용 목록 조회 전용.
행을 추가·삭제하는 것(관리자 등록·해제)은 이 코드가 아니라 운영자가 직접 SQL로 한다
— 회원가입 화면을 만들지 않기로 했으므로 앱에는 행을 만드는 경로가 없다.
**쓰는 것은 `agent_id` 한 칸뿐이다**(`decisions/314`) — 비어 있을 때만 채우고 덮어쓰지 않는다."""

from __future__ import annotations

from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.ports.output.admin_account_port import AdminAccountPort
from hub.adapter.outbound.postgres.connection import ConnectionFactory

_SELECT_BY_EMAIL = 'SELECT "id", "email", "name", "agent_id" FROM "admin_account" WHERE "email" = %s'
_SELECT_BY_ID = 'SELECT "id", "email", "name", "agent_id" FROM "admin_account" WHERE "id" = %s'
_LINK_AGENT = """
UPDATE "admin_account" SET "agent_id" = COALESCE("agent_id", %s)
WHERE "id" = %s
RETURNING "agent_id"
"""


class PostgresAdminAccountRepository(AdminAccountPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def find_by_email(self, email: str) -> AdminAccount | None:
        return await self._find_one(_SELECT_BY_EMAIL, email.lower())

    async def find_by_id(self, account_id: int) -> AdminAccount | None:
        return await self._find_one(_SELECT_BY_ID, account_id)

    async def link_agent(self, account_id: int, agent_id: str) -> str:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LINK_AGENT, (agent_id, account_id))
                row = await cur.fetchone()
            await conn.commit()
        if row is None:  # 로그인은 됐는데 행이 사라졌다 — 지어내지 않는다
            raise LookupError(f"admin_account id={account_id} 가 없다")
        return row[0]

    async def _find_one(self, sql: str, param: object) -> AdminAccount | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (param,))
                row = await cur.fetchone()
        if row is None:
            return None
        account_id, email, name, agent_id = row
        return AdminAccount(id=account_id, email=email, name=name, agent_id=agent_id)
