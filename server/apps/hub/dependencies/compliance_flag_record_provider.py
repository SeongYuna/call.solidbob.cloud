# Requirement: C-1, C-2, C-3, C-4, SEC-1, SEC-2
"""ComplianceFlagRecordPort 프로바이더 — PostgreSQL 설정이 있으면 리포지토리, 없으면 로그 어댑터.

콜 가드 기록(`call_guard_flag_record_provider`)·전사 기록과 **같은 조건**으로 가른다. 전사는 로그로 가는데
위반만 DB 로 가면 `transcript_segment` 외래키가 깨진다.
"""

from __future__ import annotations

from fastapi import Request

from hub.adapter.outbound.log_compliance_flag_record_adapter import LogComplianceFlagRecordAdapter
from hub.adapter.outbound.postgres.compliance_flag_repository import PostgresComplianceFlagRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.output.compliance_flag_record_port import ComplianceFlagRecordPort


def get_compliance_flag_record_port(request: Request) -> ComplianceFlagRecordPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        return LogComplianceFlagRecordAdapter()
    return PostgresComplianceFlagRepository(build_connection_factory(settings))
