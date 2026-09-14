# Requirement: C-6, SEC-2
"""CallGuardFlagQueryPort 프로바이더. **PostgreSQL 이 없으면 501** — 빈 목록은 «폭언이 없었다» 로 읽힌다."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.call_guard_flag_query_repository import PostgresCallGuardFlagQueryRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.input.call_guard_flag_list_use_case import CallGuardFlagListUseCase
from hub.app.ports.output.call_guard_flag_query_port import CallGuardFlagQueryPort
from hub.app.use_cases.call_guard_flag_list_interactor import CallGuardFlagListInteractor


def get_call_guard_flag_query_port(request: Request) -> CallGuardFlagQueryPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PostgreSQL 이 설정되지 않았습니다 — 콜 가드 기록을 읽을 곳이 없습니다",
        )
    return PostgresCallGuardFlagQueryRepository(build_connection_factory(settings))


def get_call_guard_flag_list_use_case(
    query_port: CallGuardFlagQueryPort = Depends(get_call_guard_flag_query_port),
) -> CallGuardFlagListUseCase:
    return CallGuardFlagListInteractor(query_port=query_port)
