# Requirement: F-3
from datetime import datetime, timezone

from customer_briefing.domain.services.briefing_checks import briefing_problems, build_messages, render_facts
from hub.app.dtos.customer_briefing_dto import BriefingFacts, PriorCall

T = datetime(2026, 10, 5, 5, 2, tzinfo=timezone.utc)
FACTS = BriefingFacts("now", True, (PriorCall(call_id="p1", started_at=T, inquiry_type="상하수도",
                                              summary_text="단수 3일째 처리 지연 문의", summary_confirmed=True,
                                              open_follow_ups=("담당 부서 회신",)),))


def test_render_has_no_ids():
    text = render_facts(FACTS)
    assert "p1" not in text and "단수 3일째" in text and "10-05" in text


def test_clean_output_passes():
    assert briefing_problems("컴플레인", "회신이 없어 다시 건 것으로 보입니다", ["지난 통화 10-05 상하수도"], render_facts(FACTS)) == []


def test_out_of_list_category():
    assert "목록 밖 범주 서류보완" in briefing_problems("서류보완", "x", ["a"], render_facts(FACTS))


def test_invented_digit():
    probs = briefing_problems("컴플레인", "5일째 지연", ["a"], render_facts(FACTS))
    assert any("재료에 없는 숫자 5" in p for p in probs)


def test_masked_digits_do_not_count():
    assert briefing_problems("재문의", "번호 ****로 문의", ["a"], "번호 **** 문의") == []


def test_forbidden_and_shape():
    assert any("금지 표현" in p for p in briefing_problems("컴플레인", "위험 고객입니다", ["a"], ""))
    assert any("줄 수" in p for p in briefing_problems("재문의", "x", [], ""))
    assert any("줄 수" in p for p in briefing_problems("재문의", "x", ["a", "b", "c", "d"], ""))


def test_messages_list_categories():
    msgs = build_messages(FACTS)
    assert "후속 확인" in msgs[0]["content"] and "단수 3일째" in msgs[1]["content"]
