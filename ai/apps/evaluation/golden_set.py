# Requirement: E-1
"""골든셋(JSON)을 로드해서 항목별 타입으로 돌려준다.

골든셋 자체는 이 저장소의 golden-set/v1-10.json이며, 스펙은 golden-set/README.md
(= 데이터 확보 계획 5.3절)와 동일하다. 이 모듈은 그 JSON을 채점 코드가 쓰기 편한
형태로만 파싱한다 — 정답을 스스로 만들어내지 않는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_GOLDEN_SET_PATH = (
    Path(__file__).resolve().parents[3] / "golden-set" / "v1-150.json"
)


@dataclass(frozen=True)
class ComplianceViolation:
    type: str
    phrase: str
    expected_alternative_source: str | None = None


@dataclass(frozen=True)
class PiiPattern:
    pattern: str  # P1~P7
    raw_span: str
    masked_expected: bool


@dataclass(frozen=True)
class CallGuardCase:
    """C-6 — **고객** 발화의 폭언·위기 신호. C-1~C-4(상담원 발화)와 방향이 반대다.

    `type` 은 `DASAN-MANUAL-5.1~5.4` 가 나눈 대응 갈래를 그대로 쓴다. 특히 `distress`
    (자해·극단적 선택 암시)는 **폭언과 다르게 다뤄야 하므로** 같은 라벨로 뭉치지 않는다
    (5.4조 — 통화를 끊지 않고 전문 기관으로 연결한다).
    """

    type: str  # "insult" | "threat" | "sexual" | "distress"
    phrase: str
    source: str | None = None


@dataclass(frozen=True)
class F2Case:
    closure_type: str
    evidence: dict[str, bool]
    expected_verdict: str  # "approved" | "blocked"
    expected_missing: list[str]
    source: str | None = None


@dataclass(frozen=True)
class GoldenItem:
    id: str
    module: str
    domain: str | None = None  # "finance" | "dasan" | "shopping" | "health"
    customer_utterance: str | None = None
    agent_utterance: str | None = None
    utterance_end_ms: int | None = None
    # 이 발화 앞에 오간 말. **검색 질의를 만들 때 함께 넣는다.**
    # 2026-09-09 AI Hub 다산 실제 발화를 훑다가 넣었다 — 서류 문의의 상당수가
    # "필요한 서류가 있나요?"·"어떤서류가 필요한가요?" 처럼 **단독으로는 무엇에 대한
    # 질문인지 알 수 없는 중간 턴**이다. 이런 발화를 그대로 질의로 쓰면 검색이 실패하는
    # 것이 당연해지고, 우리가 재는 것이 "검색 성능"이 아니라 "발화가 자족적인가"가 된다.
    # `decisions/201` 이 B 를 「대화 맥락으로 절차를 판정」이라고 적은 그대로다.
    context_utterances: list[str] = field(default_factory=list)
    trigger_examples: list[dict] = field(default_factory=list)
    expected_doc_ids: list[str] = field(default_factory=list)
    distractor_doc_ids: list[str] = field(default_factory=list)
    compliance_violation: ComplianceViolation | None = None
    pii_patterns: list[PiiPattern] = field(default_factory=list)
    f2_case: F2Case | None = None
    # C-6 콜 가드 — 고객 발화의 폭언·위기 신호. 없으면 None(정상 발화).
    call_guard: "CallGuardCase | None" = None
    notes: str | None = None


def load_golden_set(path: Path | str = DEFAULT_GOLDEN_SET_PATH) -> list[GoldenItem]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items: list[GoldenItem] = []
    for entry in raw["items"]:
        cv = entry.get("compliance_violation")
        f2 = entry.get("f2_case")
        cg = entry.get("call_guard")
        items.append(
            GoldenItem(
                id=entry["id"],
                module=entry["module"],
                domain=entry.get("domain"),
                customer_utterance=entry.get("customer_utterance"),
                agent_utterance=entry.get("agent_utterance"),
                utterance_end_ms=entry.get("utterance_end_ms"),
                context_utterances=entry.get("context_utterances", []),
                trigger_examples=entry.get("trigger_examples", []),
                expected_doc_ids=entry.get("expected_doc_ids", []),
                distractor_doc_ids=entry.get("distractor_doc_ids", []),
                compliance_violation=(
                    ComplianceViolation(**cv) if cv else None
                ),
                pii_patterns=[
                    PiiPattern(**p) for p in entry.get("pii_patterns", [])
                ],
                f2_case=(F2Case(**f2) if f2 else None),
                call_guard=(CallGuardCase(**cg) if cg else None),
                notes=entry.get("notes"),
            )
        )
    return items
