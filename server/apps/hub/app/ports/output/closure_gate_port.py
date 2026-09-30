# Requirement: F-2
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.closure_verdict_dto import ClosureVerdict


class ClosureGatePort(ABC):
    """F-2. 절차와 서류별 안내 여부로 체크리스트를 판정한다. 규칙 계산 → def.
    규칙표에 없는 절차는 ValueError — 판정을 지어내지 않는다."""

    @abstractmethod
    def evaluate(
        self, call_id: str, procedure: str, evidence: dict[str, bool], reason: str | None = None
    ) -> ClosureVerdict: ...

    def title_of(self, procedure: str) -> str | None:
        """절차 조항의 제목(규칙표). 지난 통화 보기가 조항 ID 대신 제목을 보이게(2026-10-01). 모르면 None — 지어내지 않는다."""
        return None
