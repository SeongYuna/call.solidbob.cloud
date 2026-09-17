# Requirement: F-2
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequiredDocsDetectionCommand:
    """상담원 발화로 안내 여부를 **자동 판정**하는 요청. `agent_utterances` 는 그 통화 상담원 확정 발화의 **마스킹본**이다.

    콜 미디에이터가 통화 동안 모은다 — 발화가 쌓일수록 같은 절차를 다시 판정해 `missing` 이 줄어드는 것을 화면이 본다.
    """

    call_id: str
    procedure: str
    agent_utterances: tuple[str, ...]
