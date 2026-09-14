# Requirement: F-2
from __future__ import annotations

from abc import ABC, abstractmethod


class RequiredDocsDetectionPort(ABC):
    """상담원 발화(마스킹본)에서 절차의 필수 서류를 **안내했는지** 본다. 규칙 계산 → def.
    돌려주는 dict 의 키는 서류 이름 — 곧바로 `ClosureGatePort.evaluate` 의 evidence 가 된다."""

    @abstractmethod
    def detect(self, procedure: str, agent_utterances: tuple[str, ...]) -> dict[str, bool]: ...
