# Requirement: J-5, SEC-2
"""AgentRoutingPort 프로바이더 — 블랙리스트 스포크의 PostgreSQL 어댑터. **DB 가 없으면 501** — 블랙리스트 여부를 모르고 배정하면 J-5 가 아니다."""

from __future__ import annotations

from blacklist.adapter.outbound.postgres_agent_routing_adapter import PostgresAgentRoutingAdapter
from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.input.routing_decision_use_case import RoutingDecisionUseCase
from hub.app.ports.output.agent_routing_port import AgentRoutingPort
from hub.app.use_cases.routing_decision_interactor import RoutingDecisionInteractor


def get_agent_routing_port(request: Request) -> AgentRoutingPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                            detail="PostgreSQL 이 설정되지 않았습니다 — 블랙리스트 여부를 볼 수 없어 배정하지 않습니다")
    return PostgresAgentRoutingAdapter(build_connection_factory(settings))


def get_routing_decision_use_case(routing: AgentRoutingPort = Depends(get_agent_routing_port)) -> RoutingDecisionUseCase:
    return RoutingDecisionInteractor(routing=routing)
