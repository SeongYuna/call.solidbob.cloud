# Requirement: J-5
"""J-5 인입 배정 판정 요청·결과 — 나르기만 한다(`decisions/313`). 판정 자체는 블랙리스트 도메인(`routing.route`)이 한다."""

from __future__ import annotations

from dataclasses import dataclass, field

from .blacklist_dto import RoutingDecision

MAX_CANDIDATES = 200


@dataclass(frozen=True)
class RoutingDecisionCommand:
    call_id: str  # 통화 시작(POST /hub/calls, 발신 번호 → 고객 식별)이 먼저 와 있어야 한다
    candidate_ids: tuple[str, ...]  # 지금 받을 수 있는 상담사 — 부르는 쪽(교환기)이 안다. 서버는 대기 상태를 모른다


@dataclass(frozen=True)
class RoutedCall:
    call_id: str
    decision: RoutingDecision
    customer_identified: bool  # False 면 발신 번호가 안 넘어왔거나 HMAC 키가 없다 — 블랙리스트 여부를 볼 수 없었다
    veteran_years: float  # 이번 판정에 쓴 기준
    unknown_candidates: tuple[str, ...] = field(default_factory=tuple)  # agent 에 없는 ID — 후보에서 빠졌다
