# Requirement: D-1, D-2, D-3, SEC-2
"""PostcallRecordPort 프로바이더 — PostgreSQL 이 있으면 리포지토리, 없으면 로그. 전사·판정 기록과 같은 조건이다."""

from __future__ import annotations

from fastapi import Request

from hub.adapter.outbound.log_postcall_record_adapter import LogPostcallRecordAdapter
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.postcall_repository import PostgresPostcallRepository
from hub.app.ports.output.postcall_record_port import PostcallRecordPort


def get_postcall_record_port(request: Request) -> PostcallRecordPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        return LogPostcallRecordAdapter()
    return PostgresPostcallRepository(build_connection_factory(settings))
