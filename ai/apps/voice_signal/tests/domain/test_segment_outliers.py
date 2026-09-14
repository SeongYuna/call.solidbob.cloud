# Requirement: D-5, QUA-1
"""저장 단위 판정 — 튄 발화를 **segment_id 로** 가리키고, 판정하지 않은 것을 「튄 구간 없음」과 섞지 않는다."""

import pytest

from voice_signal.domain.services.outlier import DEFAULT_THRESHOLD, MIN_BASELINE_UTTERANCES, segment_outliers


def test_튄_발화를_목록_위치가_아니라_segment_id_로_가리킨다():
    samples = [(sid, 180.0 + (sid % 3)) for sid in range(101, 121)] + [(205, 420.0)]
    result = segment_outliers("customer", samples)
    assert result.baseline_usable
    assert [o.segment_id for o in result.outliers] == [205]
    [o] = result.outliers
    assert abs(o.robust_z) >= DEFAULT_THRESHOLD
    assert o.baseline_n == len(samples)


def test_기준선을_못_만들면_판정하지_않았다고_말한다():
    samples = [(i, 180.0) for i in range(MIN_BASELINE_UTTERANCES - 1)] + [(99, 500.0)]
    result = segment_outliers("customer", samples[: MIN_BASELINE_UTTERANCES - 1])
    assert result.baseline_usable is False
    assert result.outliers == ()


def test_같은_발화를_두_번_넣으면_거부한다():
    with pytest.raises(ValueError):
        segment_outliers("agent", [(1, 180.0), (1, 180.0)] + [(i, 180.0) for i in range(2, 10)])
