# Requirement: C-6
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .call_guard_dto import ABUSE_CATEGORIES, DISTRESS_CATEGORY

DEFAULT_LIMIT = 100
MAX_LIMIT = 500
CATEGORIES = ABUSE_CATEGORIES + (DISTRESS_CATEGORY,)


@dataclass(frozen=True)
class CallGuardFlagListQuery:
    call_id: str | None = None
    category: str | None = None
    limit: int = DEFAULT_LIMIT
    offset: int = 0


@dataclass(frozen=True)
class CallGuardFlagRecord:
    """저장된 신호 1건 — `call_guard_flag` 행. `phrase` 는 마스킹된 자막에서 잘라낸 것이다."""

    id: int
    call_id: str
    segment_id: int
    category: str
    phrase: str
    span: tuple[int, int]
    source_doc_id: str | None
    detected_at: datetime


@dataclass(frozen=True)
class CallGuardFlagPage:
    flags: tuple[CallGuardFlagRecord, ...] = field(default_factory=tuple)
    total: int = 0
    limit: int = DEFAULT_LIMIT
    offset: int = 0
