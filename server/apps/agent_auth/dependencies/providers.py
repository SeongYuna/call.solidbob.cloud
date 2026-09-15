# Requirement: J-1, SEC-2
"""agent_auth 포트 → 구체 구현. **PostgreSQL 이 없으면 501** — 가짜 저장소로 대신하면 아무 토큰이나
통과하는 구멍이 된다(admin_auth 프로바이더와 같은 이유)."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from agent_auth.adapter.outbound.postgres.agent_token_repository import PostgresAgentTokenRepository
from agent_auth.app.ports.output.agent_token_port import AgentTokenPort
from hub.adapter.outbound.postgres.connection import build_connection_factory


def get_agent_token_port(request: Request) -> AgentTokenPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PostgreSQL 이 설정되지 않았습니다 — 상담원 토큰을 확인할 수 없습니다",
        )
    return PostgresAgentTokenRepository(build_connection_factory(settings))
