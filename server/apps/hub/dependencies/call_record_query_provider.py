# Requirement: B-5, D-1, F-2, SEC-2
"""CallRecordPort(통화 기록 **조회**) 프로바이더. **PostgreSQL 설정이 없으면 501** — 빈 기록은 «이 통화에 아무 일도 없었다» 로 읽혀 DB 미설정과 구분되지 않는다.

⚠ `call_record_provider.py` 와 다르다 — 그쪽은 통화 **시작** 기록(`CallStartRecordPort`)이다.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.call_record_repository import PostgresCallRecordRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.input.call_record_use_case import CallRecordUseCase
from hub.app.ports.output.call_record_port import CallRecordPort
from hub.app.use_cases.call_record_interactor import CallRecordInteractor


def get_call_record_query_port(request: Request) -> CallRecordPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PostgreSQL 이 설정되지 않았습니다 — infra/README.md 참고",
        )
    return PostgresCallRecordRepository(build_connection_factory(settings))


def get_call_record_use_case(record_port: CallRecordPort = Depends(get_call_record_query_port)) -> CallRecordUseCase:
    return CallRecordInteractor(record_port=record_port)
