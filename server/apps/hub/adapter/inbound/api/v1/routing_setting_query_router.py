# Requirement: J-5
"""GET /hub/routing-settings — 지금 적용되는 베테랑 배정 기준(관리자). 저장값이 없으면 기본값을 `saved: "false"` 로."""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from fastapi import APIRouter, Depends

from hub.adapter.inbound.api.schemas.routing_setting_schema import RoutingSettingResponse
from hub.app.ports.input.routing_setting_query_use_case import RoutingSettingQueryUseCase
from hub.dependencies.routing_setting_provider import get_routing_setting_query_use_case

routing_setting_query_router = APIRouter(prefix="/hub", tags=["hub"])


@routing_setting_query_router.get("/routing-settings", response_model=RoutingSettingResponse, dependencies=[Depends(require_admin)])
async def get_routing_setting(
    use_case: RoutingSettingQueryUseCase = Depends(get_routing_setting_query_use_case),
) -> RoutingSettingResponse:
    return RoutingSettingResponse.from_dto(await use_case.get())
