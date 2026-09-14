# Requirement: F-2
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.closure_verdict_dto import ClosureVerdict
from hub.app.dtos.required_docs_detection_dto import RequiredDocsDetectionCommand


class RequiredDocsDetectionUseCase(ABC):
    """F-2 필요서류 체크리스트 — 상담원 발화로 안내 여부를 **자동 판정**하고 게이트에 넘긴다."""

    @abstractmethod
    async def check(self, command: RequiredDocsDetectionCommand) -> ClosureVerdict: ...
