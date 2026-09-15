# Requirement: C-5, E-3
"""오류 섞인 전사의 C-5 «살아남음» 규칙 — 가짜 통과가 나지 않는지."""

from __future__ import annotations

import pytest

from evaluation.metrics.masking_robustness import classify, score, survives


class TestNumeric:
    def test_verbalized_number_still_survives(self):
        # 하네스 기준(원문 조각이 그대로 있는가)이면 여기서 가짜 통과가 난다
        assert survives("P4", "01012345678", "번호는 공일공 1234 5678 이에요")

    def test_separator_split_number_survives(self):
        assert survives("P4", "010-2345-6789", "010 2345 6789")

    def test_masked_number_does_not_survive(self):
        assert not survives("P4", "01012345678", "번호는 *********** 이에요")

    def test_partial_last_four_survive_is_leak(self):
        assert survives("P4", "01012345678", "번호는 *******5678 이에요")

    def test_three_digits_are_not_enough(self):
        assert not survives("P1", "9001011234567", "900 그리고 ****")

    def test_short_code_needs_all_digits(self):
        assert survives("P5", "4821", "인증번호 4821") and not survives("P5", "4821", "인증번호 48 요")

    def test_sino_reading_counts_but_scattered_particles_do_not(self):
        # 한 글자씩 띄워 읽은 번호도 번호다(애매하면 살아있다고 본다)
        assert survives("P5", "2525", "이 오 이 오") and survives("P5", "2525", "이오이오")
        # 떨어져 있는 "이"·"오" 한 글자는 조사·말끝이다 — 숫자로 읽지 않는다
        assert not survives("P5", "2525", "이것은 오늘 이야기 오전")


class TestHangul:
    def test_name_two_chars_is_leak(self):
        assert survives("P6", "최지훈", "저는 최지** 이고요")

    def test_jamo_changed_name_with_two_chars_left(self):
        assert survives("P6", "최지훈", "저는 최지훙이고요")

    def test_masked_name(self):
        assert not survives("P6", "최지훈", "저는 ***이고요")

    def test_address_road_left_is_leak(self):
        assert survives("P7", "성북구 정릉로 77길 12", "*** 정릉로 *** ** 에서")

    def test_address_masked(self):
        assert not survives("P7", "성북구 정릉로 77길 12", "*** *** *** ** 에서")


class TestClassify:
    def test_erased_by_injection_is_not_a_pass(self):
        case = classify("GS-1", "P6", "최지훈", injected="저는 이고요", masked="저는 이고요")
        assert case.outcome == "erased"
        s = score([case])
        assert s["miss_count"] == 0 and s["erased_count"] == 1 and s["judged"] == 0

    def test_missed_and_masked(self):
        cases = [
            classify("GS-1", "P4", "01012345678", "공일공 1234 5678", "공일공 1234 5678"),
            classify("GS-2", "P4", "01012345678", "01012345678", "***********"),
        ]
        s = score(cases)
        assert s["miss_count"] == 1 and s["missed_items"] == ["GS-1(P4)"]
        assert s["by_pattern"] == {"P4": {"masked": 1, "missed": 1, "erased": 0}}

    def test_empty_raw_span_rejected(self):
        with pytest.raises(ValueError):
            survives("P6", "", "텍스트")
