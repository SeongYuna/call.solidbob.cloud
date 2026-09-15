# Requirement: J-5
from __future__ import annotations

from hub.app.dtos.routing_setting_dto import MAX_VETERAN_YEARS, MIN_VETERAN_YEARS, RoutingSetting, RoutingSettingCommand
from hub.app.ports.input.routing_setting_use_case import RoutingSettingUseCase
from hub.app.ports.output.routing_setting_port import RoutingSettingPort


class RoutingSettingInteractor(RoutingSettingUseCase):
    def __init__(self, settings: RoutingSettingPort) -> None:
        self._settings = settings

    async def save(self, command: RoutingSettingCommand) -> RoutingSetting:
        if not MIN_VETERAN_YEARS <= command.veteran_years <= MAX_VETERAN_YEARS:
            raise ValueError(f"근속 기준은 {MIN_VETERAN_YEARS}~{MAX_VETERAN_YEARS}년이어야 합니다: {command.veteran_years}")
        return await self._settings.save(command.veteran_years, command.updated_by)
