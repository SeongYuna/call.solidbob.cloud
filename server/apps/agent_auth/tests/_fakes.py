# Requirement: J-1, QUA-1
"""메모리 속 `AgentTokenPort` — 저장된 해시를 들여다볼 수 있어 «원문이 저장되지 않는다» 를 검증한다."""

from __future__ import annotations

from datetime import datetime, timezone

from agent_auth.app.dtos.agent_directory_dto import AgentSummary
from agent_auth.app.dtos.agent_token_dto import AgentTokenItem, UnknownAgentError
from agent_auth.app.ports.output.agent_directory_port import AgentDirectoryPort
from agent_auth.app.ports.output.agent_token_port import AgentTokenPort
from agent_auth.domain.services.agent_token import hash_token

NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


class FakeAgentTokens(AgentTokenPort):
    def __init__(self, agents=("agent-7",)):
        self.agents = set(agents)
        self.rows: list[dict] = []

    def seed(self, agent_id: str, token: str) -> None:
        """테스트용 — 이미 발급된 토큰을 넣어 둔다(해시로)."""
        self.rows.append({"id": len(self.rows) + 1, "agent_id": agent_id, "token_hash": hash_token(token),
                          "issued_by": 1, "issued_at": NOW, "revoked_at": None})

    def _item(self, row) -> AgentTokenItem:
        return AgentTokenItem(id=row["id"], agent_id=row["agent_id"], issued_by=row["issued_by"],
                              issued_at=row["issued_at"], revoked_at=row["revoked_at"])

    async def save(self, agent_id, token_hash, issued_by):
        if agent_id not in self.agents:
            raise UnknownAgentError(agent_id)
        row = {"id": len(self.rows) + 1, "agent_id": agent_id, "token_hash": token_hash,
               "issued_by": issued_by, "issued_at": NOW, "revoked_at": None}
        self.rows.append(row)
        return self._item(row)

    async def find_active_agent_id(self, token_hash):
        return next((r["agent_id"] for r in self.rows if r["token_hash"] == token_hash and r["revoked_at"] is None), None)

    async def list(self, agent_id):
        return [self._item(r) for r in reversed(self.rows) if agent_id is None or r["agent_id"] == agent_id]

    async def revoke(self, token_id):
        row = next((r for r in self.rows if r["id"] == token_id), None)
        if row is None:
            return None
        row["revoked_at"] = row["revoked_at"] or NOW
        return self._item(row)


class FakeAgentDirectory(AgentDirectoryPort):
    def __init__(self, agents: dict[str, str] | None = None) -> None:
        self.agents = agents or {}

    async def list(self) -> list[AgentSummary]:
        return [AgentSummary(agent_id=aid, display_name=name) for aid, name in sorted(self.agents.items(), key=lambda kv: kv[1])]
