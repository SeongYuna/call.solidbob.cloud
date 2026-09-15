# Requirement: J-5
from __future__ import annotations

from hub.app.dtos.routing_setting_dto import RoutingSetting
from hub.app.ports.input.routing_setting_query_use_case import RoutingSettingQueryUseCase
from hub.app.ports.output.routing_setting_port import RoutingSettingPort


class RoutingSettingQueryInteractor(RoutingSettingQueryUseCase):
    def __init__(self, settings: RoutingSettingPort) -> None:
        self._settings = settings

    async def get(self) -> RoutingSetting:
        return await self._settings.get()
