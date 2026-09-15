# Requirement: J-4
"""등록 만료의 **누적 상한** — 연장을 몇 번 하든 만료는 승인일로부터 365일을 넘지 못한다(`decisions/309` 추가, 2026-09-15).

`decisions/309` 가 남겨 둔 구멍이다: 변경 1회 상한(365일)만으로는 연장을 되풀이해 사실상 영구 표시를 만들 수 있었다.
더 길게 두어야 하면 **새 요청 + 새 근거로 재등록**한다 — 그때 승인일이 새로 찍힌다. 순수 파이썬이다(`.importlinter` 계약 4).
"""

from __future__ import annotations

from datetime import datetime, timedelta

MAX_DAYS_FROM_APPROVAL = 365  # 승인 일수 상한(`blacklist_decision_dto.MAX_EXPIRES_IN_DAYS`)과 같은 값 — 승인 때 줄 수 있는 최대를 연장으로 넘지 못한다


def latest_allowed_expiry(approved_at: datetime) -> datetime:
    return approved_at + timedelta(days=MAX_DAYS_FROM_APPROVAL)


def within_cap(approved_at: datetime, new_expires_at: datetime) -> bool:
    """단축은 늘 통과한다(상한보다 앞이다). 경계(정확히 365일)는 허용한다."""
    return new_expires_at <= latest_allowed_expiry(approved_at)
