# Requirement: J-5
"""PUT /hub/routing-settings — 관리자가 베테랑 배정 기준(근속 연수)을 저장한다(`decisions/313`). 다음 배정 판정부터 쓴다."""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.routing_setting_schema import RoutingSettingRequest, RoutingSettingResponse
from hub.app.dtos.routing_setting_dto import RoutingSettingCommand
from hub.app.ports.input.routing_setting_use_case import RoutingSettingUseCase
from hub.dependencies.routing_setting_provider import get_routing_setting_use_case

routing_setting_router = APIRouter(prefix="/hub", tags=["hub"])


@routing_setting_router.put("/routing-settings", response_model=RoutingSettingResponse)
async def save_routing_setting(
    body: RoutingSettingRequest,
    admin: AdminAccount = Depends(require_admin),
    use_case: RoutingSettingUseCase = Depends(get_routing_setting_use_case),
) -> RoutingSettingResponse:
    try:
        saved = await use_case.save(RoutingSettingCommand(veteran_years=body.veteran_years, updated_by=admin.id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return RoutingSettingResponse.from_dto(saved)
