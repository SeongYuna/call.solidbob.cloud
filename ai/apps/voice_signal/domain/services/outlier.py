# Requirement: D-5
"""통화 온도 — **화자 자신의 기준선 대비** 얼마나 튀었는가를 발화 단위로 판정한다.

`decisions/203`. 「감정분석」이라는 말을 쓰지 않는 이유가 이 파일에 그대로 있다 —
여기서 하는 일은 **신호의 이상 구간 탐지**이지 심리 상태 추정이 아니다.

## 왜 절대 임계값을 쓰지 않는가

목소리 높이는 사람마다 다르다. 「220Hz 를 넘으면 흥분」 같은 규칙은 여성 화자를 통화
내내 흥분 상태로 만들고 저음 남성은 소리를 질러도 안 걸린다. **기준선을 통화 안에서,
화자별로 만든다.**

## 왜 평균이 아니라 중앙값·MAD 인가

평균과 표준편차를 쓰면 **튀는 값 자체가 기준선을 끌어올려 자기를 가린다.** 발화 20건 중
3건에서 고함을 질렀다면 그 3건이 평균을 올리고 표준편차를 키워서, 결국 「평균 대비 크게
벗어나지 않음」이 된다. 중앙값과 MAD 는 절반이 오염되기 전까지 흔들리지 않는다.

## 상담사 쪽이 기준선이 되는 구조

검토에서 나온 지적 그대로다 — **상담사는 베테랑이라 톤이 일정하다.** 화자별로 기준선을
만들면 상담사의 MAD 는 작고 고객의 MAD 는 크다. 같은 규칙을 두 화자에 똑같이 적용해도
**튀는 구간은 고객 쪽에서만 나온다.** 화자를 차별하는 규칙을 따로 두지 않아도 된다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# 정규분포에서 MAD × 1.4826 ≈ 표준편차. 로버스트 z 점수의 관례적 배율이다.
MAD_TO_SIGMA = 1.4826

# MAD 가 0 일 때 쓰는 대체 척도. 중앙값 기준 평균절대편차 × 1.2533 ≈ 표준편차.
#
# ⚠ 2026-09-09 테스트가 잡아낸 구멍이다. **값의 절반 이상이 똑같으면 MAD 가 0** 이 되고,
# 그러면 「판정 불가」로 빠진다 — 그런데 그건 **튀는 한 건이 가장 뚜렷한 경우**다.
# 톤이 일정한 상담사(설계상 그런 사람이다)에게 정확히 이 일이 일어난다.
MEANAD_TO_SIGMA = 1.2533

# 이 값을 넘으면 「튀었다」로 본다. 3.5 는 로버스트 이상치 탐지의 관례값이며
# **우리가 재서 고른 값이 아니다** — 데이터가 쌓이면 다시 정한다(절대 원칙 2).
DEFAULT_THRESHOLD = 3.5

# 기준선을 만들려면 최소 이만큼의 발화가 있어야 한다. 그 아래면 판정하지 않는다 —
# 발화 3건의 중앙값은 기준선이 아니다.
MIN_BASELINE_UTTERANCES = 8


@dataclass(frozen=True)
class Baseline:
    """한 화자의 통화 내 기준선.

    `scale` 은 z 점수의 분모다. 보통은 MAD 에서 오지만, **MAD 가 0 이면 평균절대편차로
    떨어진다** — 값이 전부 똑같아 그것마저 0 이면 그때는 정말 판정 불가다.
    """

    median: float
    mad: float
    scale: float
    n: int

    @property
    def usable(self) -> bool:
        return self.n >= MIN_BASELINE_UTTERANCES and self.scale > 0


@dataclass(frozen=True)
class Deviation:
    """발화 하나의 이탈 정도. **점수를 화면에 내지 않는다**(부록 A-1) — 내부 판정용이다."""

    index: int
    value: float
    robust_z: float

    @property
    def is_outlier(self) -> bool:
        return abs(self.robust_z) >= DEFAULT_THRESHOLD


def build_baseline(values: list[float] | np.ndarray) -> Baseline:
    """nan 을 버리고 중앙값·MAD 를 낸다. 표본이 모자라면 `usable` 이 False 다."""
    arr = np.asarray(list(values), dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return Baseline(float("nan"), 0.0, 0.0, 0)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    scale = mad * MAD_TO_SIGMA
    if scale == 0:
        scale = float(np.mean(np.abs(arr - median))) * MEANAD_TO_SIGMA
    return Baseline(median, mad, scale, len(arr))


def deviations(values: list[float] | np.ndarray, baseline: Baseline) -> list[Deviation]:
    """기준선 대비 로버스트 z 점수. 기준선을 못 쓰면 **빈 목록**이다.

    ⚠ 빈 목록은 「튄 구간이 없다」가 아니라 **「판정하지 않았다」**다. 부르는 쪽이
    `baseline.usable` 을 함께 봐야 한다 — 하네스의 `NO_SAMPLES` 와 같은 구분이다
    (절대 원칙 10).
    """
    if not baseline.usable:
        return []
    scale = baseline.scale
    out = []
    for i, v in enumerate(values):
        if v is None or np.isnan(v):
            continue
        out.append(Deviation(i, float(v), (float(v) - baseline.median) / scale))
    return out


@dataclass(frozen=True)
class SpeakerTemperature:
    """한 화자의 통화 온도 요약. `decisions/203` 이 화면에 내보내기로 한 형태다 —
    **구간 수와 인덱스**이고 점수가 아니다."""

    speaker: str
    baseline_usable: bool
    utterance_count: int
    spread: float                 # 기준선의 척도. 「이 화자가 얼마나 흔들렸는가」
    outlier_indices: tuple[int, ...]

    @property
    def outlier_count(self) -> int:
        return len(self.outlier_indices)


def summarize_speaker(speaker: str, values: list[float]) -> SpeakerTemperature:
    """발화별 특징값 목록 → 그 화자의 통화 온도 요약."""
    baseline = build_baseline(values)
    devs = deviations(values, baseline)
    return SpeakerTemperature(
        speaker=speaker,
        baseline_usable=baseline.usable,
        utterance_count=baseline.n,
        spread=baseline.scale,
        outlier_indices=tuple(d.index for d in devs if d.is_outlier),
    )
