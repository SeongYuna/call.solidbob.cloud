# Requirement: E-4, QUA-2
"""기준선 게이트 — 아래면 실패, 표본 없음은 실패도 통과도 아님, 절대 규칙은 1건이면 실패."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_baseline as cb  # noqa: E402


def _report(**over):
    base = {
        "retrieval": {"recall_at_k": 0.9, "mrr": 0.7, "n": 96},
        "masking": {"absolute_rule_passed": True, "missed_items": [], "miss_count": 0},
        "closure_gate": {"absolute_rule_passed": True, "failed_items": [], "n": 99},
    }
    base.update(over)
    return base


def test_pass_when_at_or_above_baseline():
    fails, passes, unmeasured = cb.check(_report())
    assert not fails and len(passes) == 4 and not unmeasured


def test_fail_when_recall_below_baseline():
    fails, _, _ = cb.check(_report(retrieval={"recall_at_k": 0.5, "mrr": 0.7, "n": 96}))
    assert any("recall_at_k" in f for f in fails)


def test_unmeasured_is_neither_pass_nor_fail():
    fails, passes, unmeasured = cb.check(_report(retrieval="측정 불가 — 골든셋에 채점 대상이 없다"))
    assert not any("retrieval" in f for f in fails)
    assert not any("retrieval" in p for p in passes)
    assert any("retrieval" in u for u in unmeasured)


def test_absolute_rule_one_miss_fails():
    fails, _, _ = cb.check(_report(masking={"absolute_rule_passed": False, "missed_items": ["GS-9(P4)"], "miss_count": 1}))
    assert any("masking" in f and "GS-9(P4)" in f for f in fails)
