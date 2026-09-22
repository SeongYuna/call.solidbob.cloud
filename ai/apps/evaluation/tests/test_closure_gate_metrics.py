# Requirement: F-2, QUA-1
from evaluation.metrics.closure_gate import F2Prediction, score_closure_gate


def test_exact_match_passes():
    pred = F2Prediction(
        item_id="GS-009",
        expected_verdict="incomplete",
        predicted_verdict="incomplete",
        expected_missing=["약정혜택소멸_안내", "고객확인_기록"],
        predicted_missing=["고객확인_기록", "약정혜택소멸_안내"],  # 순서 달라도 통과
    )
    result = score_closure_gate([pred])
    assert result["accuracy"] == 1.0
    assert result["absolute_rule_passed"] is True


def test_wrong_verdict_fails_absolute_rule():
    pred = F2Prediction(
        item_id="GS-009",
        expected_verdict="incomplete",
        predicted_verdict="complete",
        expected_missing=["약정혜택소멸_안내"],
        predicted_missing=[],
    )
    result = score_closure_gate([pred])
    assert result["accuracy"] == 0.0
    assert result["absolute_rule_passed"] is False
    assert result["failed_items"] == ["GS-009"]


def test_correct_verdict_but_wrong_missing_fields_still_fails():
    # verdict만 맞고 근거 필드 설명이 틀리면 F-2의 "설명 신뢰성"이 깨진다 — 실패로 본다.
    pred = F2Prediction(
        item_id="GS-009",
        expected_verdict="incomplete",
        predicted_verdict="incomplete",
        expected_missing=["약정혜택소멸_안내", "고객확인_기록"],
        predicted_missing=["약정혜택소멸_안내"],
    )
    result = score_closure_gate([pred])
    assert result["absolute_rule_passed"] is False
