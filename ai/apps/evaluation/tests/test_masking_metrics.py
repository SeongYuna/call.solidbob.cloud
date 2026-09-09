# Requirement: C-5, QUA-1
from evaluation.metrics.masking import MaskingCase, find_misses, over_masking_rate, score_masking


def test_no_misses_passes_absolute_rule():
    cases = [
        MaskingCase("GS-006", "P1", should_be_masked=True, was_masked=True),
        MaskingCase("GS-006", "P2", should_be_masked=True, was_masked=True),
    ]
    result = score_masking(cases)
    assert result["miss_count"] == 0
    assert result["absolute_rule_passed"] is True


def test_single_miss_fails_absolute_rule():
    # 절대 규칙(6.2절 원칙 4) — 999개 맞아도 1개 놓치면 실패.
    cases = [MaskingCase(f"GS-{i}", "P4", should_be_masked=True, was_masked=True) for i in range(999)]
    cases.append(MaskingCase("GS-999", "P4", should_be_masked=True, was_masked=False))
    result = score_masking(cases)
    assert result["miss_count"] == 1
    assert result["absolute_rule_passed"] is False
    # 2026-09-09: 어느 **패턴**이 뚫렸는지가 함께 찍힌다. 항목 ID 만으로는 한 발화에
    # 여러 패턴이 있을 때 무엇을 못 잡았는지 알 수 없다.
    assert result["missed_items"] == ["GS-999(P4)"]


def test_find_misses_ignores_correctly_unmasked_cases():
    cases = [MaskingCase("GS-001", "P1", should_be_masked=False, was_masked=False)]
    assert find_misses(cases) == []


def test_over_masking_rate_is_reference_only():
    cases = [
        MaskingCase("GS-001", "P1", should_be_masked=False, was_masked=True),  # 과잉 마스킹
        MaskingCase("GS-002", "P1", should_be_masked=False, was_masked=False),
    ]
    assert over_masking_rate(cases) == 0.5


# ── 가려졌는데 이름이 다른 경우 (2026-09-09) ──────────────────────────────

def test_다른_패턴으로_가려진_것은_누락이_아니다():
    """절대 규칙이 지키는 것은 **값이 노출되지 않는 것**이지 패턴 이름을 맞히는 것이 아니다.

    골든셋 150건 확장에서 실제로 나왔다 — `"집 전화 0221234567"` 이 P4 가 아니라
    P3(계좌번호)로 잡힌다. 자막에서 값은 전부 가려졌는데 예전 채점기는 「누락」으로 셌고,
    그 가짜 위반이 절대 규칙을 빨갛게 만들어 **진짜 누락을 그 안에 묻었다.**
    """
    cases = [MaskingCase("GS-409", "P4", should_be_masked=True,
                         was_masked=True, pattern_matched=False)]
    result = score_masking(cases)
    assert result["miss_count"] == 0
    assert result["absolute_rule_passed"] is True
    assert result["pattern_mismatch_count"] == 1
    assert result["pattern_mismatch_items"] == ["GS-409(P4)"]


def test_안_가려졌으면_이름과_무관하게_누락이다():
    cases = [MaskingCase("GS-412", "P6", should_be_masked=True,
                         was_masked=False, pattern_matched=False)]
    result = score_masking(cases)
    assert result["miss_count"] == 1
    assert result["absolute_rule_passed"] is False
