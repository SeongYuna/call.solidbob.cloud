# Requirement: C-1, C-2, C-3, C-4, D-1
from __future__ import annotations

from abc import ABC, abstractmethod


class ComplianceFlagQueryPort(ABC):
    """한 통화에서 컴플라이언스 위반이 잡힌 발화 번호(2026-10-01). 통화 후 요약이 그 발화를 「안내」로 싣지 않게.
    저장된 사실만 읽는다 — 여기서 검사를 다시 돌리지 않는다."""

    @abstractmethod
    async def flagged_segment_ids(self, call_id: str) -> frozenset[int]: ...
