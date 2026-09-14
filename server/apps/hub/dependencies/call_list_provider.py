# Requirement: D-1, D-2, SEC-2
"""CallListPort 프로바이더. **PostgreSQL 설정이 없으면 501** — 빈 목록은 «통화가 없다» 로 읽혀 DB 미설정과 구분되지 않는다."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.call_list_repository import PostgresCallListRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.input.call_list_use_case import CallListUseCase
from hub.app.ports.output.call_list_port import CallListPort
from hub.app.use_cases.call_list_interactor import CallListInteractor


def get_call_list_port(request: Request) -> CallListPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PostgreSQL 이 설정되지 않았습니다 — infra/README.md 참고",
        )
    return PostgresCallListRepository(build_connection_factory(settings))


def get_call_list_use_case(list_port: CallListPort = Depends(get_call_list_port)) -> CallListUseCase:
    return CallListInteractor(list_port=list_port)
