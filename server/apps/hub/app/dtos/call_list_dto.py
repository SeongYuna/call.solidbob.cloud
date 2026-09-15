# Requirement: D-1, D-2
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@dataclass(frozen=True)
class CallListQuery:
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    # 재상담 고객 이력 — `call.customer_id` 는 통화 시작에 발신 번호가 넘어온 통화만 채워진다(decisions/304)
    customer_id: str | None = None


@dataclass(frozen=True)
class CallListItem:
    """목록 한 줄 — `call` 행 그대로. 요약 본문(`summary_text`)은 싣지 않는다 — 목록에서 필요한 건 유형까지다."""

    call_id: str
    domain: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    stt_engine: str
    channel_count: int
    customer_id: str | None
    inquiry_type: str | None  # D-2 — 통화 후 처리 전이면 None
    summary_confirmed: bool  # D-1~D-3 초안을 상담원이 확정했는가 (`summary_confirmed_at` NOT NULL)


@dataclass(frozen=True)
class CallListPage:
    calls: tuple[CallListItem, ...] = field(default_factory=tuple)
    total: int = 0
    limit: int = DEFAULT_LIMIT
    offset: int = 0
