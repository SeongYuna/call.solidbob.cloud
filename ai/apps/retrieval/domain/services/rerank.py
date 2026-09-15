# Requirement: B-3
"""리랭킹 순서 규칙 — 점수를 받아 다시 세운다. 점수를 내는 모델은 adapter 에 있다.

순수 파이썬이다(`ai/.importlinter` 계약 3). **동점이면 원래 순위를 지킨다** — 모델 점수가
같을 때 실행마다 순서가 달라지면 MRR 이 흔들린다(절대 원칙 1 — 재현 가능해야 한다).
"""

from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")


def reorder(items: Sequence[T], scores: Sequence[float]) -> list[tuple[T, float]]:
    """점수 내림차순, 동점은 원래 순서. `(항목, 점수)` 목록."""
    if len(items) != len(scores):
        raise ValueError(f"항목 {len(items)}개 ≠ 점수 {len(scores)}개")
    order = sorted(range(len(items)), key=lambda i: (-scores[i], i))
    return [(items[i], scores[i]) for i in order]
