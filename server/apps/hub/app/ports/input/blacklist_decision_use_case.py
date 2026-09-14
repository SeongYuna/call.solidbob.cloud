# Requirement: J-4
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_decision_dto import BlacklistDecisionCommand
from hub.app.dtos.blacklist_dto import BlacklistRequest


class BlacklistDecisionUseCase(ABC):
    """관리자가 요청을 승인(→ 등록 에피소드)하거나 반려한다. 사람이 결정한다 — 시스템은 판정하지 않는다."""

    @abstractmethod
    async def decide(self, command: BlacklistDecisionCommand) -> BlacklistRequest: ...
