# Requirement: 7.3절 전사 이벤트, SEC-2
"""CallStartRecordPort 프로바이더 — PostgreSQL 설정이 있으면 리포지토리, 없으면 로그 어댑터.
`transcript_record_provider` 와 같은 조건으로 갈린다 — 전사가 DB 로 가는데 통화만 로그로 가면 FK 가 깨진다."""

from __future__ import annotations

from fastapi import Request

from hub.adapter.outbound.log_call_start_record_adapter import LogCallStartRecordAdapter
from hub.adapter.outbound.postgres.call_repository import PostgresCallRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.output.call_start_record_port import CallStartRecordPort


def get_call_record_port(request: Request) -> CallStartRecordPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        return LogCallStartRecordAdapter()
    return PostgresCallRepository(build_connection_factory(settings))
