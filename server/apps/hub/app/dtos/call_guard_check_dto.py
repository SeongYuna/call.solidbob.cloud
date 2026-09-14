# Requirement: C-6
from __future__ import annotations

from dataclasses import dataclass

from .call_guard_dto import CallGuardFlag


@dataclass(frozen=True)
class CallGuardCheckCommand:
    """콜 가드 검사 입력. **마스킹된 고객 발화만** 받는다.

    - 고객 발화만 — 상담원 발화는 C-1~C-4(`ComplianceCheckCommand`)가 본다. 방향이 반대다(`decisions/201`)
    - 마스킹된 본문만 — 잡힌 `phrase` 가 그대로 DB·화면에 남기 때문이다(MANUAL-5.5, SEC-1)
    """

    call_id: str
    segment_id: int
    customer_utterance: str


@dataclass(frozen=True)
class CallGuardCheckResult:
    """검사 결과. `flags` 가 비어 있으면 **"잡힌 것이 없다"**이지 "안전하다"가 아니다(부록 A-1)."""

    call_id: str
    segment_id: int
    flags: tuple[CallGuardFlag, ...] = ()
