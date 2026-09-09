# Requirement: D-5
"""음성에서 톤 특징을 뽑는다 — 기본주파수(F0)·에너지·유성음 비율.

**모델이 없다.** 자기상관과 RMS 뿐이고 학습된 가중치가 한 개도 없다. `decisions/203` 이
「판정은 규칙」(절대 원칙 9)을 지키기로 한 그대로이며, `.importlinter` 계약 3 이 금지하는
라이브러리(torch·transformers…)를 하나도 쓰지 않는다. numpy 는 선형대수 계산기이지
프레임워크가 아니다.

## 왜 F0 와 에너지인가

`decisions/203` 의 가설: **상담사의 톤은 일정하고 고객의 톤은 흔들린다.** 「톤」을 잴 수
있는 형태로 바꾸면 ① 목소리 높이(F0) ② 크기(에너지) 둘이다. 사람이 격해질 때 둘 다
올라가고, 무엇보다 **전사 텍스트에 전혀 남지 않는다** — 그래서 C-1~C-6 과 겹치지 않는
새 정보다.

## 8kHz 협대역에서 F0 를 잴 수 있는가

전화망은 대략 300~3,400Hz 만 통과시킨다. **F0 자체(남성 80~150Hz)는 그 아래로 잘려
나간다.** 그래도 자기상관은 동작한다 — 배음(2·3배 성분)이 대역 안에 살아 있고 그 간격이
곧 주기이기 때문이다. 다만 **저음 남성에서 옥타브 오류(2배 높게 잡음)가 늘어난다.**
그래서 ① 절대값을 쓰지 않고 **화자 자신의 중앙값 대비 변화**만 보고(`outlier.py`)
② 유성음으로 판정된 프레임 비율(`voiced_ratio`)을 함께 내보내 신뢰도를 판단하게 한다.
확인되지 않은 것을 확인된 것처럼 쓰지 않는다(절대 원칙 10).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# 사람 목소리의 기본주파수 범위. 이 밖은 잡음으로 본다.
F0_MIN_HZ = 60.0
F0_MAX_HZ = 400.0

FRAME_MS = 32.0   # 60Hz 한 주기(16.7ms)의 두 배 이상이어야 자기상관 봉우리가 보인다
HOP_MS = 10.0

# 유성음 판정 — 자기상관 봉우리가 이만큼은 뚜렷해야 주기가 있다고 본다.
VOICING_THRESHOLD = 0.35

# 옥타브 보정을 적용할 조건 — 배음으로 되돌린 값이 원래 값보다 **이 배 이상** 기준에
# 가까워질 때만 바꾼다. 애매하면 원래 값을 남긴다.
#
# ⚠ 2026-09-09 첫 판에서는 「기준 대비 1.6배 창을 벗어나면 되돌리거나 버린다」로 썼는데
# **거의 모든 값이 되돌려졌다.** 창의 폭이 1.6² = 2.56 배라 옥타브(2배) 간격보다 넓어서,
# 어떤 값이든 ×2 나 ÷2 중 하나는 창 안에 들어왔다. 그러면 **진짜 억양의 극단값까지
# 스냅**되고, 우리가 재려는 것이 바로 그 억양 폭이라 측정 대상을 스스로 깎게 된다.
OCTAVE_FIX_GAIN = 2.0
# 무음 판정 — 프레임 RMS 가 그 발화 최대치의 이 비율 아래면 말이 없는 구간으로 본다.
SILENCE_RATIO = 0.08


@dataclass(frozen=True)
class VoiceFeatures:
    """발화 하나의 톤 요약. **점수가 아니다** — 물리량과 그 분산이다(부록 A-1)."""

    duration_s: float
    voiced_ratio: float       # 유성음 프레임 비율 — 낮으면 아래 F0 값을 믿지 않는다
    f0_median_hz: float       # 목소리 높이의 대표값
    f0_spread_hz: float       # p90 - p10. **얼마나 흔들렸는가**
    energy_median_db: float
    energy_spread_db: float

    @property
    def is_reliable(self) -> bool:
        """유성음이 너무 적으면 F0 통계를 쓰지 않는다. 잡음·무음에서 나온 값이다."""
        return self.voiced_ratio >= 0.15


def _frames(samples: np.ndarray, rate: int) -> np.ndarray:
    size = int(rate * FRAME_MS / 1000)
    hop = int(rate * HOP_MS / 1000)
    if len(samples) < size:
        return np.empty((0, size), dtype=np.float64)
    count = 1 + (len(samples) - size) // hop
    idx = np.arange(size)[None, :] + hop * np.arange(count)[:, None]
    return samples[idx]


def _frame_f0(frame: np.ndarray, rate: int) -> float:
    """자기상관으로 프레임 하나의 F0 를 낸다. 주기가 안 보이면 nan.

    평균을 빼고(DC 제거) 자기상관을 구한 뒤, F0 범위에 해당하는 지연(lag) 구간에서
    가장 큰 봉우리를 찾는다. 봉우리 높이를 0 지연 값으로 나눠 정규화한 것이 유성음
    판정 기준이다 — 잡음은 봉우리가 뚜렷하지 않다.
    """
    frame = frame - frame.mean()
    norm = float(np.dot(frame, frame))
    if norm <= 0:
        return float("nan")

    corr = np.correlate(frame, frame, mode="full")[len(frame) - 1 :]
    lag_min = max(1, int(rate / F0_MAX_HZ))
    lag_max = min(len(corr) - 1, int(rate / F0_MIN_HZ))
    if lag_max <= lag_min:
        return float("nan")

    window = corr[lag_min : lag_max + 1]
    peak = int(np.argmax(window))
    if window[peak] / norm < VOICING_THRESHOLD:
        return float("nan")
    return rate / (lag_min + peak)


def _fix_octave_errors(f0: np.ndarray) -> np.ndarray:
    """배음을 F0 로 잘못 잡은 프레임을 되돌리거나 버린다.

    **왜 필요한가** (2026-09-09 실측으로 알았다): 8kHz 협대역에서는 F0 자체가 대역 아래로
    잘려 자기상관이 2배·3배 배음에 걸리는 일이 잦다. 보정 없이 재니 **발화 하나 안의
    F0 폭(p90-p10)이 100Hz** 로 나왔다 — 사람이 한 문장 안에서 그렇게 오르내리지 않는다.
    억양을 잰 것이 아니라 **추정기의 오류를 잰 것**이었고, 그 상태로 상담사·민원인을
    비교하면 둘 다 오류에 파묻혀 차이가 안 보인다.

    방법: 유성음 프레임들의 중앙값을 기준으로 삼고, 2배·1/2배·3배·1/3배 중 **기준에
    확실히 더 가까워지는**(`OCTAVE_FIX_GAIN` 배 이상) 후보가 있을 때만 되돌린다.
    중앙값을 기준으로 쓰는 이유는 `outlier.py` 와 같다 — 오류가 절반을 넘지 않는 한
    기준이 흔들리지 않는다.

    **애매하면 원래 값을 남긴다.** 억양의 극단값을 지우면 우리가 재려는 폭 자체가
    줄어든다 — 측정 대상을 측정 도구가 깎는 모양이 된다(절대 원칙 10).
    F0 범위 밖으로 나간 값만 버린다.
    """
    voiced = f0[~np.isnan(f0)]
    if len(voiced) < 3:
        return f0

    center = float(np.median(voiced))
    fixed = f0.copy()
    for i, v in enumerate(f0):
        if np.isnan(v):
            continue
        if not (F0_MIN_HZ <= v <= F0_MAX_HZ):
            fixed[i] = np.nan
            continue

        here = abs(np.log2(v / center))
        best, best_dist = v, here
        for c in (v / 2.0, v * 2.0, v / 3.0, v * 3.0):
            if not (F0_MIN_HZ <= c <= F0_MAX_HZ):
                continue
            d = abs(np.log2(c / center))
            if d < best_dist:
                best, best_dist = c, d
        # 확실히 더 가까워질 때만 바꾼다. 조금 나아지는 정도면 억양일 수 있다.
        fixed[i] = best if best_dist * OCTAVE_FIX_GAIN <= here else v
    return fixed


def extract(samples: np.ndarray, rate: int) -> VoiceFeatures:
    """발화 하나(모노 float 배열, -1~1) → 톤 요약.

    **무음 프레임을 먼저 버린다.** 통화 녹음은 앞뒤에 침묵이 붙는데 그 구간을 섞으면
    에너지 중앙값이 통째로 내려가고, 「말이 없었다」가 「조용히 말했다」로 기록된다.
    """
    if rate <= 0:
        raise ValueError(f"표본율이 올바르지 않다: {rate}")
    samples = np.asarray(samples, dtype=np.float64).ravel()
    duration = len(samples) / rate

    frames = _frames(samples, rate)
    if len(frames) == 0:
        return VoiceFeatures(duration, 0.0, *(float("nan"),) * 4)

    rms = np.sqrt((frames ** 2).mean(axis=1))
    loud = rms > (rms.max() * SILENCE_RATIO)
    if not loud.any():
        return VoiceFeatures(duration, 0.0, *(float("nan"),) * 4)

    speech = frames[loud]
    speech_rms = rms[loud]

    f0 = np.array([_frame_f0(f, rate) for f in speech])
    f0 = _fix_octave_errors(f0)
    voiced = f0[~np.isnan(f0)]
    voiced_ratio = len(voiced) / len(speech)

    # 0 나눗셈·log(0) 을 피한다. 무음은 이미 걸러졌지만 방어적으로 둔다.
    db = 20.0 * np.log10(np.maximum(speech_rms, 1e-10))

    return VoiceFeatures(
        duration_s=duration,
        voiced_ratio=voiced_ratio,
        f0_median_hz=float(np.median(voiced)) if len(voiced) else float("nan"),
        f0_spread_hz=(float(np.percentile(voiced, 90) - np.percentile(voiced, 10))
                      if len(voiced) >= 4 else float("nan")),
        energy_median_db=float(np.median(db)),
        energy_spread_db=float(np.percentile(db, 90) - np.percentile(db, 10)),
    )
