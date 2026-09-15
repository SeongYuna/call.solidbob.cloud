# Requirement: D-1, D-2, D-3
"""확정된 요약 **재수정** — 확정은 한 번이지만 틀린 확정은 고칠 수 있어야 한다. 고치기 전 값은 이력으로 남는다(`decisions/311`).

누가 고쳤는지는 담지 않는다 — 확정과 같은 이유(부록 A-1, 상담원 단위 집계 금지).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

REASON_MAX_CHARS = 500  # db `call_summary_revision.reason` VARCHAR(500)


@dataclass(frozen=True)
class SummaryRevisionCommand:
    call_id: str
    summary_text: str  # 새 요약 — 저장 전 마스킹
    reason: str  # 왜 고치는가 — 필수, 저장 전 마스킹
    inquiry_type: str | None = None
    follow_up_actions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SummaryRevision:
    """고치기 **전** 값 한 벌 + 사유. 새 값은 `call` 에 있다."""

    revision_id: int
    call_id: str
    previous_summary_text: str
    previous_inquiry_type: str | None
    reason: str
    revised_at: datetime


@dataclass(frozen=True)
class SummaryRevised:
    call_id: str
    summary_text: str
    inquiry_type: str | None
    follow_up_actions: tuple[str, ...]
    revision: SummaryRevision
