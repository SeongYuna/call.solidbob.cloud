# Requirement: C-5
"""NER 태거가 내놓는 토큰 태그와, 그것을 합쳐 만든 개인정보 구간.

순수 파이썬이다(`ai/.importlinter` 계약 3). 모델이 무엇이든 이 형태로만 넘어오면
`domain/services/spans.py` 의 규칙이 그대로 돈다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenTag:
    """서브워드 토큰 하나의 판정. `start`/`end` 는 **원문 문자 오프셋**이다.

    `label` 은 `"PER"`·`"LOC"` 처럼 **BIO 접두·접미를 뗀 개체 유형**이다. 모델마다
    `B-PER`·`PER-B` 처럼 표기가 달라서(`monologg/koelectra-base-v3-naver-ner` 는 뒤에 붙인다)
    어댑터가 떼어서 넘긴다. `"O"` 는 넘기지 않아도 된다.
    """

    start: int
    end: int
    label: str
    score: float = 1.0


@dataclass(frozen=True)
class EntitySpan:
    """P6·P7 구간 1건. `[start, end)` 원문 문자 오프셋 — 마스킹은 자리수를 보존하므로
    마스킹 후 텍스트 기준으로도 같다(7.3절)."""

    pattern: str  # "P6" | "P7"
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError(f"구간이 올바르지 않습니다: {self.pattern} ({self.start}, {self.end})")
