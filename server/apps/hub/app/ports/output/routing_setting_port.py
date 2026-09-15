# Requirement: J-5
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.routing_setting_dto import RoutingSetting


class RoutingSettingPort(ABC):
    """베테랑 배정 기준 저장·조회. 저장값이 없으면 기본값을 `saved=False` 로 돌려준다."""

    @abstractmethod
    async def get(self) -> RoutingSetting: ...

    @abstractmethod
    async def save(self, veteran_years: float, updated_by: int) -> RoutingSetting: ...
