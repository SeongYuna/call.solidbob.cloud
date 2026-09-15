# Requirement: J-1
"""상담원 토큰 DTO — 나르기만 한다. 필드명은 db `agent_token` 과 같다. **목록 항목에는 토큰도 해시도 없다.**"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AgentTokenItem:
    id: int
    agent_id: str
    issued_by: int | None  # admin_account.id — 누가 발급했는가
    issued_at: datetime
    revoked_at: datetime | None  # NULL 이면 유효


@dataclass(frozen=True)
class IssuedAgentToken:
    item: AgentTokenItem
    token: str  # 원문 — 이 응답으로 한 번만 나간다. 저장하지 않는다


@dataclass(frozen=True)
class IssueAgentTokenCommand:
    agent_id: str
    issued_by: int


class UnknownAgentError(Exception):
    """`agent` 에 없는 상담원이다 — 토큰을 발급할 대상이 없다."""


class AgentTokenNotFound(Exception):
    """그런 토큰 id 가 없다."""
