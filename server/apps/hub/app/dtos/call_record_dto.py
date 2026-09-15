# Requirement: B-5, D-1, D-2, D-3, F-2
"""통화 1건의 저장 기록 — 상담기록 화면이 지난 통화를 다시 볼 때 쓴다. 나르기만 한다.

**저장된 것만 담는다.** 전사는 `GET /hub/calls/{id}/transcript` 가 따로 준다(페이지가 길다).
감정분석(D)·통번역(A-5)은 저장되지 않으므로 여기 없다 — 없는 것을 빈 값으로 채우지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SavedCard:
    card_id: int
    rank: int
    title: str
    summary: str
    source_doc_id: str | None  # `document` 에 없는 조항이면 NULL 로 저장됐다(decisions/308)
    similarity_score: float | None


@dataclass(frozen=True)
class SavedRecommendation:
    recommendation_id: int
    trigger_at_ms: int
    internal_latency_ms: int | None
    created_at: datetime
    cards: tuple[SavedCard, ...] = field(default_factory=tuple)  # 비었으면 「관련 문서 없음」(B-6)


@dataclass(frozen=True)
class SavedClosureItem:
    rank: int
    document_name: str
    informed: bool


@dataclass(frozen=True)
class SavedClosure:
    closure_id: int
    procedure: str
    verdict: str  # complete | incomplete
    detected: bool
    reason: str | None
    source_doc_id: str | None
    decided_at: datetime
    items: tuple[SavedClosureItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SavedFollowUp:
    action_text: str
    status: str  # draft = 규칙·모델 초안


@dataclass(frozen=True)
class CallRecord:
    call_id: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    summary_text: str | None  # D-1 초안. 통화 후 처리 전이면 None
    inquiry_type: str | None
    summary_confirmed_at: datetime | None  # None 이면 초안이다
    follow_up_actions: tuple[SavedFollowUp, ...] = field(default_factory=tuple)
    recommendations: tuple[SavedRecommendation, ...] = field(default_factory=tuple)
    closures: tuple[SavedClosure, ...] = field(default_factory=tuple)


class CallRecordNotFound(LookupError):
    """그런 통화가 없다."""
