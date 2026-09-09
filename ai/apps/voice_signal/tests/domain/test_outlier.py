# Requirement: D-5
"""통화 온도 판정. **로버스트 통계를 쓰는 이유가 테스트로 남아 있어야** 나중에
「평균이 더 간단한데 왜 안 썼지」로 되돌아가지 않는다."""

from __future__ import annotations

import numpy as np

from voice_signal.domain.services.outlier import (
    MIN_BASELINE_UTTERANCES,
    build_baseline,
    deviations,
    summarize_speaker,
)


# ── 왜 중앙값·MAD 인가 ───────────────────────────────────────────────────
def test_튀는_값이_기준선을_끌어올리지_못한다():
    """평균·표준편차를 쓰면 **튀는 값 자체가 기준선을 올려 자기를 가린다.**
    발화 20건 중 3건에서 고함을 질렀다면 그 3건이 평균을 올리고 표준편차를 키워서
    결국 「크게 벗어나지 않음」이 된다."""
    values = [180.0] * 17 + [400.0, 410.0, 420.0]
    baseline = build_baseline(values)
    assert baseline.median == 180.0

    outliers = [d for d in deviations(values, baseline) if d.is_outlier]
    assert len(outliers) == 3

    # 대조 — 평균/표준편차였다면 몇 건이나 잡혔을까
    arr = np.array(values)
    z = np.abs((arr - arr.mean()) / arr.std())
    assert (z >= 3.5).sum() == 0, "평균 기준으로는 한 건도 안 잡힌다 — 그래서 안 쓴다"


def test_정말_전부_같으면_판정하지_않는다():
    """척도가 0 이면 z 점수가 무한대가 된다. 「전부 이상」이 아니라 「못 잰다」다."""
    baseline = build_baseline([180.0] * 20)
    assert baseline.scale == 0
    assert not baseline.usable
    assert deviations([180.0] * 20, baseline) == []


def test_MAD가_0이어도_한_건이_튀면_잡는다():
    """⚠ 2026-09-09 테스트가 잡아낸 구멍. **값의 절반 이상이 똑같으면 MAD 가 0** 이라
    「판정 불가」로 빠지는데, 그건 **튀는 한 건이 가장 뚜렷한 경우**다.
    톤이 일정한 상담사(설계상 그런 사람이다)에게 정확히 이 일이 일어난다."""
    values = [110.0] * 12 + [190.0]
    baseline = build_baseline(values)
    assert baseline.mad == 0
    assert baseline.usable, "MAD 0 에서 평균절대편차로 떨어져야 한다"
    assert summarize_speaker("남", values).outlier_count == 1


def test_표본이_모자라면_기준선을_세우지_않는다():
    """발화 3건의 중앙값은 기준선이 아니다."""
    few = [180.0, 200.0, 160.0]
    assert not build_baseline(few).usable
    assert len(few) < MIN_BASELINE_UTTERANCES


def test_빈_목록은_이상_없음이_아니라_판정_안_함이다():
    """⚠ 부르는 쪽이 `baseline.usable` 을 함께 봐야 한다 — 하네스의 `NO_SAMPLES` 와
    같은 구분이다(절대 원칙 10)."""
    values = [180.0, 190.0]
    baseline = build_baseline(values)
    assert deviations(values, baseline) == []
    assert not baseline.usable  # ← 이걸 안 보면 「이상 0건」으로 읽힌다


# ── 화자별 기준선이라 절대 임계값이 필요 없다 ────────────────────────────
def test_저음_화자와_고음_화자가_같은_규칙으로_판정된다():
    """「220Hz 를 넘으면 흥분」 같은 절대 규칙은 여성 화자를 통화 내내 흥분으로 만들고
    저음 남성은 소리를 질러도 안 걸린다."""
    low = [110.0] * 12 + [190.0]      # 저음 화자가 크게 올린 한 건
    high = [230.0] * 12 + [310.0]     # 고음 화자가 같은 비율로 올린 한 건
    assert summarize_speaker("남", low).outlier_count == 1
    assert summarize_speaker("여", high).outlier_count == 1


def test_톤이_일정한_화자는_기준선이_좁다():
    """`decisions/203` 의 구조 — 상담사 쪽 MAD 가 작고 민원인 쪽이 크다.
    같은 규칙을 두 화자에 똑같이 적용해도 튀는 구간은 한쪽에서만 나온다."""
    steady = summarize_speaker("상담사", [200.0, 201.0, 199.0, 200.0, 202.0,
                                          198.0, 200.0, 201.0, 199.0, 200.0])
    swingy = summarize_speaker("민원인", [180.0, 240.0, 150.0, 300.0, 170.0,
                                          260.0, 190.0, 220.0, 160.0, 280.0])
    assert steady.spread < swingy.spread


def test_nan_은_건너뛴다():
    """유성음이 없어 F0 가 안 잡힌 발화가 섞인다. 0 으로 치면 전부 이상치가 된다."""
    values = [180.0, float("nan"), 182.0, 179.0, 181.0, 180.0, 183.0, 178.0, 180.0]
    assert build_baseline(values).n == 8


def test_요약에_점수가_아니라_구간_수가_담긴다():
    """부록 A-1 — 화면에 위험도 점수를 내지 않는다. 나가는 것은 구간 목록이다."""
    t = summarize_speaker("민원인", [180.0] * 12 + [400.0])
    assert t.outlier_indices == (12,)
    assert not hasattr(t, "score")
