# Requirement: D-1, D-2, E-1
"""D-1 요약 · D-2 유형 채점 — **규칙만 쓴다. LLM 채점 금지**(절대 원칙 1, `decisions/218`).

- **핵심 항목 포함률(D-1)**: 골든셋이 통화마다 적어 둔 핵심 항목(문의 절차·필요서류 핵심·안내·조치·고객 요청) 하나하나에
  «허용 표기» 몇 개를 붙여 두고, 요약에 그중 하나라도 **글자 그대로** 들어 있으면 포함으로 센다.
  비교 전에 양쪽을 정규화한다 — 소문자로, 한글·영문·숫자가 아닌 글자(공백·문장부호·`*` 가림 문자)는 지운다.
  그래서 「전입 신고」·「전입신고」·「전입신고,」 는 같은 표기다. 뜻이 같은 **다른 말**은 허용 표기에 적힌 것만 잡는다.
- **유형 일치(D-2)**: 정답 유형과 글자까지 같아야 맞다. 요약기가 **모든 통화에서** 유형을 `None` 으로 내면
  0점이 아니라 「측정 불가」다(`TYPE_NULL`) — 분류를 안 한 것과 틀리게 분류한 것은 다른 사실이다.

⚠ 한계 — 주장 범위를 넘지 않는다.
- 표기 일치는 **극성을 모른다.** 「위임장은 필요 없어요」 에도 `위임장` 이 들어 있다. 발췌·요약이 틀린 안내를 옮겨도 포함으로 센다
- 허용 표기 밖의 바꿔 말하기(「서류 떼는 곳」 ↔ 「발급처」)는 놓친다 — 포함률은 **하한**으로 읽는다
- 요약 길이를 보지 않는다. 자막 전부를 붙인 «요약» 은 만점을 받는다 — 규칙 발췌(`decisions/306`)는 두 발화만 싣지만,
  모델 요약을 잴 때는 길이(`summary_chars`)를 함께 본다
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

TYPE_NULL = "측정 불가 — 유형이 null(`w6-d2-inquiry-type-null`)"


@dataclass(frozen=True)
class KeyItem:
    """요약에 들어 있어야 할 사실 하나. `forms` 중 하나가 요약에 있으면 포함이다."""

    id: str
    kind: str  # "문의" | "서류" | "안내" | "조치" | "요청"
    label: str
    forms: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.forms:
            raise ValueError(f"{self.id}: 허용 표기가 없다 — 어떤 요약도 이 항목을 맞힐 수 없다")
        if any(not normalize(f) for f in self.forms):
            raise ValueError(f"{self.id}: 정규화하면 빈 문자열이 되는 표기가 있다 — 모든 요약에 걸린다")


@dataclass(frozen=True)
class PostcallCase:
    call_id: str
    key_items: tuple[KeyItem, ...]
    expected_type: str
    summary: str
    predicted_type: str | None


@dataclass(frozen=True)
class CallScore:
    call_id: str
    hit: tuple[str, ...]  # KeyItem.id
    missed: tuple[str, ...]
    coverage: float
    type_correct: bool | None  # 예측 유형이 None 이면 None — 틀린 것이 아니라 내지 않은 것
    summary_chars: int = 0
    missed_labels: tuple[str, ...] = field(default=())


def normalize(text: str) -> str:
    """소문자 + 한글·영문·숫자만 남긴다. 공백·문장부호·가림 문자(`*`)는 지운다."""
    return "".join(c for c in text.lower() if c.isalnum())


def item_present(summary: str, item: KeyItem) -> bool:
    s = normalize(summary)
    return any(normalize(f) in s for f in item.forms)


def score_call(case: PostcallCase) -> CallScore:
    if not case.key_items:
        raise ValueError(f"{case.call_id}: 핵심 항목이 없다 — 포함률 분모가 0 이다")
    hit = tuple(k.id for k in case.key_items if item_present(case.summary, k))
    missed_items = [k for k in case.key_items if k.id not in hit]
    return CallScore(
        call_id=case.call_id,
        hit=hit,
        missed=tuple(k.id for k in missed_items),
        coverage=len(hit) / len(case.key_items),
        type_correct=None if case.predicted_type is None else case.predicted_type == case.expected_type,
        summary_chars=len(case.summary),
        missed_labels=tuple(k.label for k in missed_items),
    )


def score_postcall(cases: list[PostcallCase]) -> dict:
    """통화별 포함률 → 매크로 평균(통화마다 같은 무게) · 마이크로(항목 전체) · 종류별 놓친 수 · 유형 정확도."""
    if not cases:
        raise ValueError("채점할 통화가 없다 — 하네스가 NO_SAMPLES 로 먼저 걸러야 한다")
    scores = [score_call(c) for c in cases]
    total = sum(len(c.key_items) for c in cases)
    hits = sum(len(s.hit) for s in scores)

    by_kind: dict[str, list[int]] = {}
    for c, s in zip(cases, scores):
        for k in c.key_items:
            row = by_kind.setdefault(k.kind, [0, 0])
            row[1] += 1
            if k.id in s.hit:
                row[0] += 1

    typed = [s for s in scores if s.type_correct is not None]
    result: dict = {
        "n_calls": len(cases),
        "key_items": total,
        "key_items_hit": hits,
        "coverage_macro": sum(s.coverage for s in scores) / len(scores),
        "coverage_micro": hits / total,
        "summary_chars_median": statistics.median(s.summary_chars for s in scores),
        "coverage_by_kind": {k: f"{h}/{n}" for k, (h, n) in by_kind.items()},
        "per_call": {s.call_id: round(s.coverage, 3) for s in scores},
        "missed": {s.call_id: list(s.missed_labels) for s in scores if s.missed_labels},
    }
    if not typed:
        result["type_accuracy"] = TYPE_NULL
    else:
        result["type_accuracy"] = sum(1 for s in typed if s.type_correct) / len(scores)
        result["type_null"] = len(scores) - len(typed)  # 분모에는 남긴다 — 안 낸 유형은 맞힌 것이 아니다
    return result
