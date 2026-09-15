# Requirement: B-4, B-5
"""서류 목록 규칙 — 근거 대조·금지 표현·문구 조립."""

from __future__ import annotations

from generation.domain.services.document_list import (
    build_messages,
    check_items,
    compose_summary,
    is_none_answer,
    normalize,
    parse_items,
)

SOURCE = (
    "4.3 주민등록초본 발급 — 필요서류\n초본은 등본과 달리 **개인의 주소 변동 이력**을 담는다. 본인 발급은 신분증으로 신청하고, "
    "대리 발급은 **위임장, 위임인 신분증 사본, 대리인 신분증**이 필요하다."
)


def test_parse_bullets_numbers_and_commas():
    out = "필요 서류:\n- 위임장\n2) 위임인 신분증 사본, 대리인 신분증\n* **신분증**."
    assert parse_items(out) == ["위임장", "위임인 신분증 사본", "대리인 신분증", "신분증"]


def test_grounded_vs_hallucinated():
    check = check_items(["위임장", "위임인 신분증사본", "가족관계증명서"], SOURCE)
    assert check.grounded == ("위임장", "위임인 신분증사본")  # 띄어쓰기 차이는 흡수
    assert check.ungrounded == ("가족관계증명서",) and check.hallucinated == 1


def test_forbidden_terms_are_dropped_not_grounded():
    check = check_items(["위임장 100% 필요", "신분증"], SOURCE)
    assert check.forbidden == ("위임장 100% 필요",) and check.grounded == ("신분증",)


def test_none_answer():
    assert is_none_answer("없음") and is_none_answer("  없습니다. ") and not is_none_answer("- 위임장")


def test_summary_is_composed_by_code():
    assert compose_summary(("위임장", "대리인 신분증")) == "필요 서류: 위임장 · 대리인 신분증"


def test_normalize_strips_markup_and_spaces():
    assert normalize("**위임인 신분증 사본**") == "위임인신분증사본"


def test_prompt_has_source_and_instruction():
    msgs = build_messages("초본 대리 발급 서류요", "4.3 초본", "본문")
    assert msgs[0]["role"] == "system" and "빈 배열" in msgs[0]["content"]
    assert "본문" in msgs[-1]["content"] and "초본 대리 발급 서류요" in msgs[-1]["content"]
    # 예시를 넣지 않는다 — 2026-09-15 가상 예시의 말이 답에 새어 들어왔다
    assert len(msgs) == 2


def test_json_items_with_parenthetical_stripped():
    assert parse_items('{"documents": ["위임장 (대리인 서명·날인 필수)", "대리인 신분증"]}') == ["위임장", "대리인 신분증"]


def test_json_empty_is_none():
    assert is_none_answer('{"documents": []}') and not is_none_answer('{"documents": ["위임장"]}')


def test_quotes_and_leaked_template_tokens_are_stripped():
    assert parse_items('["위임장", "대리인 신분증"]<|eot_id|>') == ["위임장", "대리인 신분증"]
