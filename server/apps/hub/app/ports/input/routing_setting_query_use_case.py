# Requirement: J-5
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.routing_setting_dto import RoutingSetting


class RoutingSettingQueryUseCase(ABC):
    """지금 적용되는 베테랑 배정 기준 — 저장값이 없으면 기본값."""

    @abstractmethod
    async def get(self) -> RoutingSetting: ...
