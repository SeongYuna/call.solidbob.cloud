# Requirement: J-1
"""HTTP 표면 스키마 — 상담원 토큰 관리. 값은 전부 문자열이다(`hub` 의 `StrField` 합의와 같다).
**`token` 은 발급 응답에만 있다.** 목록·폐기 응답에는 원문도 해시도 없다."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agent_auth.app.dtos.agent_token_dto import AgentTokenItem
from hub.adapter.inbound.api.schemas._types import StrField


class IssueAgentTokenRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=20, description="agent.agent_id")


class AgentTokenItemSchema(BaseModel):
    id: StrField
    agent_id: str
    issued_by: StrField | None = Field(default=None, description="발급한 admin_account.id")
    issued_at: str
    revoked_at: str | None = Field(default=None, description="null 이면 유효")

    @staticmethod
    def from_dto(item: AgentTokenItem) -> "AgentTokenItemSchema":
        return AgentTokenItemSchema(
            id=item.id,
            agent_id=item.agent_id,
            issued_by=item.issued_by,
            issued_at=item.issued_at.isoformat(),
            revoked_at=item.revoked_at.isoformat() if item.revoked_at else None,
        )


class IssuedAgentTokenResponse(BaseModel):
    token: str = Field(description="⚠ 이 응답에서 한 번만 보인다 — 서버는 해시만 저장해 다시 보여줄 수 없다")
    item: AgentTokenItemSchema


class AgentTokenListResponse(BaseModel):
    tokens: list[AgentTokenItemSchema]
