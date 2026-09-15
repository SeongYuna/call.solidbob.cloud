# Requirement: D-1, D-2, D-3
"""통화 후 요약 **확정** — 상담원이 초안을 고쳐서 확정한다. 나르기만 한다.

`CallSummaryDraft` 가 «초안» 인 이유가 여기서 풀린다(부록 A-1: 모델·규칙이 만든 것을 시스템이 확정하지 않는다 — 사람이 한다).
**누가 확정했는지는 담지 않는다** — 카드 피드백과 같은 이유로 상담원 단위 집계를 만들 재료를 두지 않는다. 확정 요청은 상담원 토큰으로만 받는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

INQUIRY_TYPE_MAX_CHARS = 30  # db `call.inquiry_type` VARCHAR(30)
ACTION_MAX_CHARS = 200  # db `follow_up_action.action_text` VARCHAR(200)
MAX_FOLLOW_UPS = 20


@dataclass(frozen=True)
class SummaryConfirmationCommand:
    call_id: str
    summary_text: str  # 상담원이 고친(또는 그대로 둔) 요약 — 저장 전 마스킹
    inquiry_type: str | None = None
    follow_up_actions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SummaryConfirmed:
    call_id: str
    summary_text: str  # 마스킹된 저장본
    inquiry_type: str | None
    follow_up_actions: tuple[str, ...]
    confirmed_at: datetime
