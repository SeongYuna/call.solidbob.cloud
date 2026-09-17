# Requirement: J-1
"""GET /hub/agents/me 응답 — 지금 이 토큰이 누구인지."""

from __future__ import annotations

from pydantic import BaseModel


class AgentMeResponse(BaseModel):
    agent_id: str
