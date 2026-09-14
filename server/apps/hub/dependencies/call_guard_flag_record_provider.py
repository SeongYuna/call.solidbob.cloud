# Requirement: C-6, SEC-1, SEC-2
"""CallGuardFlagRecordPort 프로바이더 — PostgreSQL 설정이 있으면 리포지토리, 없으면 로그 어댑터.

전사 기록(`transcript_record_provider`)과 **같은 조건**으로 가른다. 전사는 로그로 가는데 신호만 DB 로 가면
`transcript_segment` 외래키가 깨진다.
"""

from __future__ import annotations

from fastapi import Request

from hub.adapter.outbound.log_call_guard_flag_record_adapter import LogCallGuardFlagRecordAdapter
from hub.adapter.outbound.postgres.call_guard_flag_repository import PostgresCallGuardFlagRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.output.call_guard_flag_record_port import CallGuardFlagRecordPort


def get_call_guard_flag_record_port(request: Request) -> CallGuardFlagRecordPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        return LogCallGuardFlagRecordAdapter()
    return PostgresCallGuardFlagRepository(build_connection_factory(settings))
