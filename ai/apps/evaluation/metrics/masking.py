# Requirement: C-5, E-1
"""C-5 개인정보 마스킹 채점. [평가 설계 6.1절] P1~P7 패턴 마스킹 누락은 **0건 — 절대
규칙**이다. [6.2절 원칙 4]에 따라 평균값이 아니라 1건 단위로 실패 처리한다. 과잉
마스킹률은 참고 기록일 뿐 목표가 아니다."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaskingCase:
    """채점 단위 1건 = 항목 하나 안의 패턴 하나.

    **`was_masked` 와 `pattern_matched` 를 나눠 둔 이유** (2026-09-09): 절대 규칙이 지키려는
    것은 **값이 노출되지 않는 것**이지 패턴 이름을 맞히는 것이 아니다. 실제로 골든셋
    150건 확장에서 `"집 전화 0221234567"` 이 P4 가 아니라 **P3(계좌번호)로 잡히는** 경우가
    나왔다 — 자막에서 값은 전부 가려졌는데 채점기는 「누락」으로 셌다. 그대로 두면
    **가짜 위반**이 절대 규칙을 빨갛게 만들고, 진짜 누락(규칙이 이름을 통째로 못 잡은 건)이
    그 안에 묻힌다.

    그래서 `was_masked` 는 「그 글자가 가려졌는가」, `pattern_matched` 는 「무엇으로
    불렀는가」다. **절대 규칙은 앞의 것으로만 판정하고**, 뒤의 것은 따로 센다.
    """

    item_id: str
    pattern: str  # P1~P7
    should_be_masked: bool
    was_masked: bool
    pattern_matched: bool = True


def find_misses(cases: list[MaskingCase]) -> list[MaskingCase]:
    """마스킹됐어야 하는데 안 된 케이스 — 절대 규칙 위반. 하나라도 있으면 안 된다."""
    return [c for c in cases if c.should_be_masked and not c.was_masked]


def pattern_mismatches(cases: list[MaskingCase]) -> list[MaskingCase]:
    """가려지긴 했는데 **다른 패턴 이름으로** 잡힌 케이스. 위반은 아니지만 남겨야 한다 —
    화면의 「어떤 정보를 가렸는지」 표기가 틀리고, 패턴별 커버리지 집계도 어긋난다."""
    return [c for c in cases if c.should_be_masked and c.was_masked and not c.pattern_matched]


def over_masking_rate(cases: list[MaskingCase]) -> float:
    """마스킹 안 됐어야 하는데 된 케이스 비율. 목표 수치 없음 — 참고 기록만."""
    negatives = [c for c in cases if not c.should_be_masked]
    if not negatives:
        return float("nan")
    return sum(1 for c in negatives if c.was_masked) / len(negatives)


def score_masking(cases: list[MaskingCase]) -> dict:
    misses = find_misses(cases)
    mismatched = pattern_mismatches(cases)
    return {
        "miss_count": len(misses),
        "missed_items": [f"{c.item_id}({c.pattern})" for c in misses],
        "absolute_rule_passed": len(misses) == 0,
        # 값은 가려졌으나 이름이 다른 건. **절대 규칙 판정에는 넣지 않는다** — 노출은 없었다.
        "pattern_mismatch_count": len(mismatched),
        "pattern_mismatch_items": [f"{c.item_id}({c.pattern})" for c in mismatched],
        "over_masking_rate": over_masking_rate(cases),
        "n": len(cases),
    }
