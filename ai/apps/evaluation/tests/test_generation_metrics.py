# Requirement: B-4, B-5, E-2
"""생성 채점 규칙 — 생성기 필터와 독립적으로 환각을 센다."""

from __future__ import annotations

from evaluation.metrics.generation import (
    card_hallucinations,
    forbidden_hits,
    raw_hallucinations,
    score_generation,
)

SRC = "4.3 초본 — 필요서류\n대리 발급은 위임장, 위임인 신분증 사본, 대리인 신분증이 필요하다."


def test_raw_output_fragments_not_in_source():
    assert raw_hallucinations("- 위임장\n- 가족관계증명서, 대리인 신분증", SRC) == ["가족관계증명서"]


def test_none_answer_is_zero():
    assert raw_hallucinations("없음", SRC) == []


def test_synonym_counts_as_hallucination():
    # 조항에 없는 이름을 화면에 쓴 것이다 — 의미가 같아도 센다
    assert raw_hallucinations("- 주민등록증", SRC) == ["주민등록증"]


def test_prose_answer_is_hallucination():
    # 목록 대신 문장으로 답하면 그 문장이 조항에 없으므로 센다
    assert raw_hallucinations("대리인이 오시면 됩니다", SRC) == ["대리인이 오시면 됩니다"]


def test_card_summary_items():
    assert card_hallucinations("필요 서류: 위임장 · 대리인 신분증", SRC) == []
    assert card_hallucinations("필요 서류: 위임장 · 인감증명서", SRC) == ["인감증명서"]


def test_snippet_card_is_not_scored_as_list():
    assert card_hallucinations("대리 발급은 위임장…", SRC) == []


def test_forbidden():
    assert forbidden_hits("필요 서류: 위임장 (100% 필요)") == ["%"]


def test_score_rollup():
    rows = [
        {"doc_id": "D1", "summary": "필요 서류: 위임장", "source_text": SRC, "raw_output": "- 위임장\n- 인감", "outcome": "generated"},
        {"doc_id": "D2", "summary": "원문", "source_text": SRC, "raw_output": "없음", "outcome": "none"},
        {"doc_id": "", "summary": "원문", "source_text": SRC, "raw_output": "", "outcome": "error"},
    ]
    s = score_generation(rows)
    assert s["cards"] == 3 and abs(s["source_rate"] - 2 / 3) < 1e-9
    assert s["raw_hallucinated_cards"] == 1 and s["raw_hallucinated_items"] == 1
    assert s["shipped_hallucinated_cards"] == 0
    assert s["outcomes"] == {"generated": 1, "none": 1, "no_grounded_items": 0, "error": 1}


def test_json_output_fragments_keep_parenthetical():
    # 괄호 설명도 모델이 쓴 말이다 — 원출력 환각으로 센다
    assert raw_hallucinations('{"documents": ["위임장 (서명 필수)", "대리인 신분증"]}', SRC) == ["위임장 (서명 필수)"]
    assert raw_hallucinations('{"documents": []}', SRC) == []


def test_bare_json_array_with_leaked_token():
    assert raw_hallucinations('["위임장", "인감증명서"]<|eot_id|>', SRC) == ["인감증명서"]
