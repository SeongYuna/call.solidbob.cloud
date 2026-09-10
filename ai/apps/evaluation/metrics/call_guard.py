# Requirement: C-6, E-1
"""C-6 콜 가드 채점 — **고객** 발화의 폭언·위기 신호.

C-1~C-4 와 목표는 같다(재현율 ≥0.90 · 정밀도 ≥0.60, 재현율 우선). 방향만 반대다 —
저쪽은 상담원의 금지 표현을, 이쪽은 고객의 폭언을 잡는다(`_project/decisions/201`).

**이진 재현율만으로는 부족하다.** `DASAN-MANUAL-5.4` 가 자해·극단적 선택 암시(`distress`)를
폭언과 **다르게** 다루라고 정한다 — 폭언은 안내 후 통화를 종료하지만 위기 신호는 종료하지
않고 전문 기관으로 연결한다. 그래서 "잡았다/못 잡았다" 옆에 **`distress` 를 폭언으로
잘못 분류한 건수**를 따로 센다. 이진 지표만 보면 이 오분류가 TP 로 집계돼 사라진다.

규칙으로만 계산한다(LLM 채점 배제, 6.2절 원칙 1).
"""

from __future__ import annotations

from dataclasses import dataclass

from .compliance import precision_recall

# 「폭언」으로 묶이는 갈래 — 5.1~5.2 조의 단계적 대응·종료 대상.
ABUSE_TYPES = ("insult", "threat", "sexual")
# 「위기」 갈래 — 5.4 조. 종료하지 않고 전문 기관으로 연결한다.
DISTRESS_TYPE = "distress"


@dataclass(frozen=True)
class CallGuardPrediction:
    """항목 1건. `expected_type`/`predicted_type` 은 없으면 None(정상 발화)."""

    item_id: str
    expected_type: str | None
    predicted_type: str | None


def _is_abuse(t: str | None) -> bool:
    return t in ABUSE_TYPES


def misrouted_distress(predictions: list[CallGuardPrediction]) -> list[str]:
    """위기 신호(`distress`)를 **폭언으로** 분류한 항목. 통화를 끊게 만드는 오분류다."""
    return [
        p.item_id
        for p in predictions
        if p.expected_type == DISTRESS_TYPE and _is_abuse(p.predicted_type)
    ]


def missed_distress(predictions: list[CallGuardPrediction]) -> list[str]:
    """위기 신호를 **아무것도 아닌 것으로** 넘긴 항목. 놓치면 연결 자체가 일어나지 않는다."""
    return [
        p.item_id
        for p in predictions
        if p.expected_type == DISTRESS_TYPE and p.predicted_type is None
    ]


def score_call_guard(predictions: list[CallGuardPrediction]) -> dict:
    """탐지 여부의 재현율·정밀도 + 갈래 오분류를 함께 낸다."""
    expected = [p.expected_type is not None for p in predictions]
    predicted = [p.predicted_type is not None for p in predictions]
    tp = sum(1 for e, q in zip(expected, predicted) if e and q)
    fp = sum(1 for e, q in zip(expected, predicted) if not e and q)
    fn = sum(1 for e, q in zip(expected, predicted) if e and not q)

    result = dict(precision_recall(tp, fp, fn))
    result["n"] = len(predictions)

    # 탐지한 것 중 갈래까지 맞힌 비율. 분모는 "정답이 있고 무언가 잡은" 건이다.
    detected = [p for p in predictions if p.expected_type and p.predicted_type]
    result["type_accuracy"] = (
        sum(1 for p in detected if p.expected_type == p.predicted_type) / len(detected)
        if detected
        else float("nan")
    )

    misrouted = misrouted_distress(predictions)
    missed = missed_distress(predictions)
    result["distress_misrouted"] = len(misrouted)
    result["distress_misrouted_items"] = misrouted
    result["distress_missed"] = len(missed)
    result["distress_missed_items"] = missed
    return result
