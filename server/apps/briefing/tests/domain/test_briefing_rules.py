# Requirement: F-3
from datetime import datetime, timezone

from briefing.domain.services.briefing_rules import facts_text, rule_lines, rule_purpose
from hub.app.dtos.customer_briefing_dto import BRIEFING_PURPOSES, BriefingFacts, PriorCall

T = datetime(2026, 10, 5, 5, 2, tzinfo=timezone.utc)  # KST 10-05 14:02


def _facts(*calls, blacklisted=False):
    return BriefingFacts(call_id="now", customer_identified=True, prior_calls=tuple(calls), blacklisted=blacklisted)


def _call(**kw):
    base = dict(call_id="p1", started_at=T, inquiry_type="일반행정", summary_text="고객이 위임 등본 발급을 문의했다.",
                summary_confirmed=True)
    base.update(kw)
    return PriorCall(**base)


def test_incomplete_procedure_wins():
    p = rule_purpose(_facts(_call(incomplete_procedures=("DASAN-TERM-4.1",), open_follow_ups=("회신",))))
    assert p.category == "서류 보완" and p.source == "rule"


def test_follow_up_before_complaint():
    p = rule_purpose(_facts(_call(open_follow_ups=("담당 부서 회신",), call_guard_categories=("insult",))))
    assert p.category == "후속 확인"


def test_call_guard_means_complaint():
    assert rule_purpose(_facts(_call(call_guard_categories=("insult",)))).category == "컴플레인"


def test_plain_history_is_reinquiry():
    assert rule_purpose(_facts(_call())).category == "재문의"


def test_only_latest_call_decides():
    older = _call(call_id="p0", incomplete_procedures=("DASAN-TERM-4.1",))
    latest = _call(call_id="p1")
    assert rule_purpose(_facts(latest, older)).category == "재문의"


def test_category_always_in_list():
    for f in (_facts(_call()), _facts(_call(open_follow_ups=("x",)))):
        assert rule_purpose(f).category in BRIEFING_PURPOSES


def test_rule_lines_at_most_three_and_no_forbidden_words():
    lines = rule_lines(_facts(_call(open_follow_ups=("담당 부서 회신",), incomplete_procedures=("DASAN-TERM-4.1",),
                                    call_guard_categories=("insult",)), blacklisted=True))
    assert 1 <= len(lines) <= 3
    joined = " ".join(lines)
    for bad in ("위험", "요주의", "점수", "%", "확실"):
        assert bad not in joined


def test_rule_lines_without_summaries():
    lines = rule_lines(_facts(_call(summary_text=None, inquiry_type=None, incomplete_procedures=("DASAN-TERM-4.1",))))
    assert lines and all("None" not in line for line in lines)
    assert "DASAN-TERM-4.1" in " ".join(lines)


def test_facts_text_carries_summaries_and_dates_but_no_ids():
    text = facts_text(_facts(_call()))
    assert "위임 등본" in text and "10-05" in text and "p1" not in text
