# Requirement: 7.3절 종결 판정, F-2
"""필요서류 체크리스트 판정 (F-2) — 나르기만 한다.

계약 (`plan.md` 7.3절 rev.5):
    {"call_id": "c_001", "procedure": "DASAN-TERM-4.3", "procedure_title": "주민등록초본 발급",
     "evidence": {"신분증": false}, "verdict": "incomplete", "missing": ["신분증"],
     "source": {"doc_id": "DASAN-TERM-4.3", "title": "주민등록초본 발급 — 필요서류"}, "detected": true}

- `procedure` 는 필요서류 조항 ID 다 — 추천 카드의 `source.doc_id` 와 같은 체계라 게이트웨이가 그대로 넘긴다.
- verdict·missing 이 evidence 와 맞는지는 이 DTO 가 검사하지 않는다. 규칙은 closure_gate 스포크의 domain 이 갖고
  골든셋으로 evaluation 이 채점한다(절대 규칙 — 1건이라도 어긋나면 실패). 허브는 도메인 로직을 갖지 않는다.
- 2026-09-14 `decisions/305` — `closure_type`(금융·쇼핑 처리유형)·`approved/blocked` 를 걷어냈다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .recommendation_card_dto import Source

Verdict = Literal["complete", "incomplete"]


@dataclass(frozen=True)
class ClosureVerdict:
    call_id: str
    procedure: str
    evidence: dict[str, bool]
    verdict: Verdict
    missing: tuple[str, ...] = field(default_factory=tuple)
    reason: str | None = None
    source: Source | None = None  # 판정 근거 조항 (DASAN-TERM-x.y)
    procedure_title: str | None = None
    # True 면 evidence 를 상담원 발화 키워드로 자동 판정했다 — 부정 문맥을 모른다(closure_gate detection 주석)
    detected: bool = False
    conditional: tuple[str, ...] = ()  # 조건부 추가 서류 — 판정에 넣지 않는다. 화면이 「해당하면 함께」 로 보여줄 재료
