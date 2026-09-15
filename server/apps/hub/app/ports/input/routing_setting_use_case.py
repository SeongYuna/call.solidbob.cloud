# Requirement: J-5
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.routing_setting_dto import RoutingSetting, RoutingSettingCommand


class RoutingSettingUseCase(ABC):
    """관리자가 베테랑 배정 기준(근속 연수)을 저장한다."""

    @abstractmethod
    async def save(self, command: RoutingSettingCommand) -> RoutingSetting: ...
