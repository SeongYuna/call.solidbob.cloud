# Requirement: F-2
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClosureCheckCommand:
    """체크리스트를 **호출자가 직접** 채운 판정 요청. `evidence` 키는 서류 이름이다.

    허브는 어떤 서류가 필수인지 모른다 — 규칙표는 closure_gate 스포크가 갖는다. 여기서 키를 검사하면 규칙이 두 곳에 생긴다.
    """

    call_id: str
    procedure: str
    evidence: dict[str, bool]
    reason: str | None = None
