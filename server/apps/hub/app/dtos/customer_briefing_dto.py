# Requirement: F-3
"""통화 수신 전 고객 브리핑 계약 (`decisions/220`). 나르기만 한다 — 판정·문장 만들기는 포트 뒤에 있다.

**고객 ID 를 담지 않는다.** `BriefingFacts.customer_identified` 는 «식별했는가» 만 말한다(`304`·`322`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

BRIEFING_PURPOSES: tuple[str, ...] = ("재문의", "후속 확인", "서류 보완", "컴플레인", "신규 문의")


@dataclass(frozen=True)
class PriorCall:
    call_id: str
    started_at: datetime
    inquiry_type: str | None
    summary_text: str | None          # 마스킹본에서 만든 D-1. 통화 후 처리 전이면 None
    summary_confirmed: bool
    open_follow_ups: tuple[str, ...] = ()          # status draft·confirmed 의 action_text
    incomplete_procedures: tuple[str, ...] = ()    # 절차별 마지막 판정이 incomplete 인 procedure
    call_guard_categories: tuple[str, ...] = ()    # insult·threat·sexual·distress — 문구는 싣지 않는다


@dataclass(frozen=True)
class BriefingFacts:
    call_id: str
    customer_identified: bool
    prior_calls: tuple[PriorCall, ...] = ()   # 최근순, 최대 5
    blacklisted: bool = False                 # 적용 중인 등록이 있다는 사실만


@dataclass(frozen=True)
class BriefingPurpose:
    category: str   # BRIEFING_PURPOSES 중 하나
    text: str
    source: str     # "model" | "rule"


@dataclass(frozen=True)
class BriefingComposition:
    purpose: BriefingPurpose
    lines: tuple[str, ...]


@dataclass(frozen=True)
class CustomerBriefing:
    call_id: str
    status: str   # ready | first_contact | unidentified
    prior_call_count: int
    purpose: BriefingPurpose | None
    lines: tuple[str, ...]
    evidence: tuple[PriorCall, ...]
    open_follow_ups: int
    call_guard_categories: tuple[str, ...]
    blacklisted: bool
    generated_at: datetime
    extra: dict = field(default_factory=dict, compare=False)  # 측정용(모델 소요 시간 등) — 응답에 싣지 않는다


class BriefingCallNotFound(LookupError):
    """그런 통화가 없다."""
