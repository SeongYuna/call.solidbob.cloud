# Requirement: C-6
"""C-6 판정 — **고객** 발화에서 폭언·위기 신호를 찾는다. 규칙만 쓴다(절대 원칙 9).

순서가 중요하다. **`distress` 를 먼저 본다.** 「죽여버리고 싶다」처럼 위해 표현과 위기
표현이 겹치는 말이 있는데, 5.4 조가 정한 대응(통화를 끊지 않고 전문 기관 연결)과 5.2 조가
정한 대응(즉시 종료)이 **정반대**라 잘못 고르면 위기 상황에서 전화를 끊게 된다.
놓쳤을 때의 비용이 큰 쪽을 먼저 본다.

⚠ **위험도 점수를 내지 않는다**([부록 A-1](/docs/12/)). 몇 건이 걸렸는지는 세지만
그것을 0~100 으로 환산하지 않는다 — 근거 없는 정밀함을 화면에 띄우는 것이 금지 사항이다.

순수 파이썬이다(`.importlinter` 계약 3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..value_objects.lexicon import (
    DISTRESS_EXEMPT,
    DISTRESS_PATTERNS,
    INSULT_PATTERNS,
    INSULT_TERMS,
    SEXUAL_PATTERNS,
    THREAT_PATTERNS,
)

# 근거 조항 — 갈래마다 대응이 다르므로 조항도 다르다.
SOURCE_BY_CATEGORY = {
    "insult": "DASAN-MANUAL-5.1",
    "threat": "DASAN-MANUAL-5.2",
    "sexual": "DASAN-MANUAL-5.2",
    "distress": "DASAN-MANUAL-5.4",
}


@dataclass(frozen=True)
class Detection:
    """걸린 것 1건. `phrase` 는 원문에서 잘라낸 실제 표현이다 — 사전 항목이 아니다.

    사전 항목을 그대로 돌려주면 화면에 「가만\\s*(안|못)\\s*(둬|...)」 같은 정규식이 뜬다.
    상담원이 보는 것은 고객이 실제로 한 말이어야 한다.
    """

    category: str
    phrase: str
    start: int
    end: int

    @property
    def source_doc_id(self) -> str:
        return SOURCE_BY_CATEGORY[self.category]


_COMPILED: dict[str, tuple[re.Pattern[str], ...]] = {
    "insult": tuple(re.compile(p) for p in INSULT_PATTERNS),
    "threat": tuple(re.compile(p) for p in THREAT_PATTERNS),
    "sexual": tuple(re.compile(p) for p in SEXUAL_PATTERNS),
    "distress": tuple(re.compile(p) for p in DISTRESS_PATTERNS),
}
_EXEMPT = tuple(re.compile(p) for p in DISTRESS_EXEMPT)


def _term_hits(text: str) -> list[Detection]:
    """욕설 사전 — 부분 문자열로 본다. 활용형을 전부 적지 않기 위해서다."""
    hits = []
    for term in INSULT_TERMS:
        start = text.find(term)
        if start >= 0:
            hits.append(Detection("insult", text[start : start + len(term)], start, start + len(term)))
    return hits


def _pattern_hits(text: str, category: str) -> list[Detection]:
    hits = []
    for pattern in _COMPILED[category]:
        for m in pattern.finditer(text):
            hits.append(Detection(category, m.group(0), m.start(), m.end()))
    return hits


def _is_exempt_distress(text: str, span: tuple[int, int]) -> bool:
    """관용 표현 위에서 걸린 위기 신호인가. 구간이 겹치면 면제로 본다."""
    for pattern in _EXEMPT:
        for m in pattern.finditer(text):
            if m.start() < span[1] and span[0] < m.end():
                return True
    return False


def detect(customer_utterance: str) -> list[Detection]:
    """갈래별로 훑어 걸린 것을 전부 돌려준다. 없으면 빈 목록.

    **정상 발화에 빈 목록을 돌려주는 것이 이 함수의 절반**이다. 재현율만 보고 만들면
    "전부 폭언"이라고 답하는 구현이 만점을 받는다(절대 원칙 10) — 그래서 골든셋에
    정상 발화(강한 항의·불만 표현)를 함께 실었다.
    """
    text = (customer_utterance or "").strip()
    if not text:
        return []

    found: list[Detection] = []

    # 1) 위기 신호를 먼저 — 대응이 정반대라 다른 갈래에 가려지면 안 된다.
    for hit in _pattern_hits(text, "distress"):
        if not _is_exempt_distress(text, (hit.start, hit.end)):
            found.append(hit)

    # 2) 나머지 갈래
    found += _pattern_hits(text, "threat")
    found += _pattern_hits(text, "sexual")
    found += _term_hits(text)
    found += _pattern_hits(text, "insult")

    return _dedupe(found)


def _dedupe(hits: list[Detection]) -> list[Detection]:
    """같은 구간이 여러 규칙에 걸리면 **먼저 온 것**을 남긴다.

    `detect()` 가 위기 → 위협 → 성적 → 욕설 순으로 넣으므로, 겹칠 때 살아남는 것은
    대응이 가장 다른 갈래다. 「죽여버리고 싶다」가 `threat` 로 덮이지 않는 이유가 이것이다.
    """
    kept: list[Detection] = []
    for hit in hits:
        if any(hit.start < k.end and k.start < hit.end for k in kept):
            continue
        kept.append(hit)
    return sorted(kept, key=lambda h: h.start)
