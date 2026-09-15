# Requirement: J-5, SEC-2
"""RoutingSettingPort 프로바이더 — 블랙리스트 스포크의 PostgreSQL 저장소. DB 가 없으면 501."""

from __future__ import annotations

from blacklist.adapter.outbound.postgres_routing_setting_repository import PostgresRoutingSettingRepository
from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.input.routing_setting_query_use_case import RoutingSettingQueryUseCase
from hub.app.ports.input.routing_setting_use_case import RoutingSettingUseCase
from hub.app.ports.output.routing_setting_port import RoutingSettingPort
from hub.app.use_cases.routing_setting_interactor import RoutingSettingInteractor
from hub.app.use_cases.routing_setting_query_interactor import RoutingSettingQueryInteractor


def get_routing_setting_port(request: Request) -> RoutingSettingPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="PostgreSQL 이 설정되지 않았습니다 — 설정을 저장할 곳이 없습니다")
    return PostgresRoutingSettingRepository(build_connection_factory(settings))


def get_routing_setting_use_case(port: RoutingSettingPort = Depends(get_routing_setting_port)) -> RoutingSettingUseCase:
    return RoutingSettingInteractor(settings=port)


def get_routing_setting_query_use_case(port: RoutingSettingPort = Depends(get_routing_setting_port)) -> RoutingSettingQueryUseCase:
    return RoutingSettingQueryInteractor(settings=port)
