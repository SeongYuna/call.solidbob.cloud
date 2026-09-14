# Requirement: F-2, SEC-2
"""ClosureRecordPort 프로바이더 — PostgreSQL 이 있으면 리포지토리, 없으면 로그. 전사 기록과 같은 조건이다(외래키 짝)."""

from __future__ import annotations

from fastapi import Request

from hub.adapter.outbound.log_closure_record_adapter import LogClosureRecordAdapter
from hub.adapter.outbound.postgres.closure_repository import PostgresClosureRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.output.closure_record_port import ClosureRecordPort


def get_closure_record_port(request: Request) -> ClosureRecordPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        return LogClosureRecordAdapter()
    return PostgresClosureRepository(build_connection_factory(settings))
