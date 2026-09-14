# Requirement: J-2, J-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.blacklist_request_create_dto import CallEvidence


class BlacklistEvidencePort(ABC):
    """한 통화의 근거를 저장된 사실에서 모은다 — 콜 가드 건수(`call_guard_flag`)·온도 이상(`voice_outlier`)·
    통화 길이·마스킹된 자막. 없는 통화면 None."""

    @abstractmethod
    async def collect(self, call_id: str) -> CallEvidence | None: ...
