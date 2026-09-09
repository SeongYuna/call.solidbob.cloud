# Requirement: 7.3절 추천 카드, B-5, B-6
"""추천 카드 묶음 — 트리거 1회당 1건.

계약 v2 예시:
    {"call_id": "c_001", "trigger_at_ms": 3150,
     "cards": [{"title": "프로모션 할인 적용 시점 안내",
                "summary": "신규 가입 할인은 가입 다음 달 청구서부터 반영됩니다.",
                "source": {"doc_id": "TERM-3.2", "title": "요금제약관 3.2조"}, "similarity_score": 0.87}],
     "internal_latency_ms": 780, "e2e_latency_ms": 1240}

- source 는 필수다. 출처 없는 카드는 만들 수 없다 (B-5). doc_id 는 knowledge-base 조항 ID (decisions/003 ②).
- cards 가 비어 있으면 "관련 문서 없음"(B-6)이다. 억지로 카드를 채우지 않는다.
- 폴백 모드(생성 없이 스니펫 표시)에서도 같은 형태다 — summary 에 원문 스니펫이 들어갈 뿐이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    doc_id: str  # 예: "TERM-3.2"
    title: str  # 예: "요금제약관 3.2조" — 화면 표시용


@dataclass(frozen=True)
class Card:
    title: str
    summary: str
    source: Source
    similarity_score: float  # 유사도/RRF 점수. 화면에 그대로 표시 (B-5). "위험도"가 아니다.


@dataclass(frozen=True)
class RecommendationCards:
    call_id: str
    trigger_at_ms: int
    cards: tuple[Card, ...] = field(default_factory=tuple)
    internal_latency_ms: int | None = None  # 코어 내부 처리 (트리거 → 카드 완성)
    e2e_latency_ms: int | None = None  # 발화 종료 → 화면 표시. 게이트웨이/대시보드가 채운다

    @property
    def no_relevant_document(self) -> bool:
        return not self.cards
