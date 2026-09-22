# Requirement: J-3, SEC-2
"""AdminStatsPort 프로바이더. **PostgreSQL 이 없으면 501** — 0 을 내면 «아무 일도 없었다» 로 읽힌다."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.admin_stats_repository import PostgresAdminStatsRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.input.admin_stats_use_case import AdminStatsUseCase
from hub.app.ports.output.admin_stats_port import AdminStatsPort
from hub.app.use_cases.admin_stats_interactor import AdminStatsInteractor


def get_admin_stats_port(request: Request) -> AdminStatsPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PostgreSQL 이 설정되지 않았습니다 — 셀 곳이 없습니다",
        )
    return PostgresAdminStatsRepository(build_connection_factory(settings))


def get_admin_stats_use_case(stats: AdminStatsPort = Depends(get_admin_stats_port)) -> AdminStatsUseCase:
    return AdminStatsInteractor(stats)
