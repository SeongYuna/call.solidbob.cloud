# Requirement: D-1, D-2
"""D-2 장 투표 · D-1 요약 검사."""

from __future__ import annotations

from postcall_summary.domain.services.rules import (
    INQUIRY_TYPES,
    build_messages,
    suggest_inquiry_type,
    summary_problems,
)


def test_vote_by_chapter_with_rank_weight():
    # 1위 4장(1.0) vs 2·3위 2장(0.5+0.333) — 1위가 이긴다
    assert suggest_inquiry_type(["DASAN-TERM-4.3", "DASAN-TERM-2.1", "DASAN-TERM-2.5"]) == "일반행정"
    # 2·3·4위가 모이면 1위를 넘는다 (0.5+0.333+0.25 > 1.0)
    assert suggest_inquiry_type(["DASAN-TERM-4.3", "DASAN-TERM-3.1", "DASAN-TERM-3.2", "DASAN-TERM-3.9"]) == "상하수도"


def test_manual_policy_chapter1_and_6_do_not_vote():
    assert suggest_inquiry_type(["DASAN-MANUAL-2.1", "DASAN-POLICY-1", "DASAN-TERM-1.4", "DASAN-TERM-6.2"]) is None
    assert suggest_inquiry_type(["DASAN-TERM-6.1", "DASAN-TERM-5.3"]) == "감염병"


def test_types_match_production_catalogue():
    """유형 이름은 **운영 표를 직접 읽어** 대조한다(2026-09-28, 류준 제안).

    손으로 적어 둔 목록과 맞추면 운영 표(`server/apps/postcall/.../inquiry_rules.py`)가 바뀔 때 또 갈라진다 —
    09-22 에 실제로 그렇게 갈라졌고 그때 가드는 초록이었다. 이 표의 값이 **운영 판정을 덮어쓰므로**
    (`model_postcall_adapter` 의 `suggest_inquiry_type(...) or inquiry_type`), 갈라지면 화면·DB 라벨이 틀린다.

    `⊆` 로 본다 — 운영 표에는 여기서 투표하지 않는 유형(6장 재난·생계 지원금 · 미분류)이 더 있다.
    """
    from postcall.domain.services.inquiry_rules import INQUIRY_RULES  # 운영 표를 직접 읽는다

    assert set(INQUIRY_TYPES) <= {name for name, _ in INQUIRY_RULES}
    assert set(INQUIRY_TYPES) == {"대중교통", "상하수도", "일반행정", "감염병"}  # 투표하는 넷은 그대로


def test_summary_digit_not_in_transcript():
    src = "고객: 수도요금 32150원이 나왔어요\n상담원: 가상계좌로 입금하시면 됩니다"
    assert summary_problems("수도요금 32,150원 납부 방법을 안내했다.", src) == []
    assert summary_problems("수도요금 42150원 납부 방법을 안내했다.", src) == ["자막에 없는 숫자 42150"]


def test_summary_cannot_unmask_digits():
    src = "고객: 제 번호는 ***********이에요"
    assert any("자막에 없는 숫자" in p for p in summary_problems("고객 연락처 01012345678 확인.", src))


def test_forbidden_and_empty_and_length():
    assert summary_problems("", "x") == ["빈 요약"]
    assert "금지 표현 무조건" in summary_problems("무조건 처리된다고 안내", "무조건")
    assert any(p.startswith("길이") for p in summary_problems("가" * 301, "가"))


def test_prompt_uses_masked_lines_with_roles():
    msgs = build_messages([("customer", "등본 떼려고요"), ("agent", "신분증 지참하세요")])
    assert "고객: 등본 떼려고요" in msgs[1]["content"] and "상담원: 신분증 지참하세요" in msgs[1]["content"]
