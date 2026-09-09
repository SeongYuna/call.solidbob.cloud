# Requirement: D-5
"""톤 특징 추출. **합성 신호로 검증한다** — 정답 F0 를 우리가 정하므로 추정기가 맞는지
말할 수 있다. 실제 음성으로 테스트하면 「무엇이 정답인지」부터 알 수 없다.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from voice_signal.domain.services.features import (
    _fix_octave_errors,
    extract,
)

RATE = 8000  # 전화망 표준. 우리 통화 데이터가 전부 이 값이다


def tone(f0: float, seconds: float = 1.0, rate: int = RATE, harmonics: int = 4) -> np.ndarray:
    """배음이 있는 톤. 순수 사인파는 실제 목소리와 달라 자기상관이 너무 쉽게 맞는다."""
    t = np.arange(int(rate * seconds)) / rate
    wave = sum(np.sin(2 * math.pi * f0 * k * t) / k for k in range(1, harmonics + 1))
    return wave / np.abs(wave).max()


# ── F0 추정 ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("f0", [110.0, 180.0, 240.0])
def test_기본주파수를_찾는다(f0):
    feats = extract(tone(f0), RATE)
    assert feats.is_reliable
    assert abs(feats.f0_median_hz - f0) / f0 < 0.05


def test_8kHz_에서도_저음_남성을_찾는다():
    """전화망은 300Hz 아래를 자른다. F0 100Hz 는 대역 밖인데 **배음으로 잡힌다** —
    이게 안 되면 남성 화자를 통째로 못 재고, 그 사실을 모른 채 수치를 내게 된다."""
    feats = extract(tone(100.0, harmonics=8), RATE)
    assert feats.is_reliable
    assert abs(feats.f0_median_hz - 100.0) / 100.0 < 0.08


def test_잡음에서는_주기를_주장하지_않는다():
    rng = np.random.default_rng(20260909)
    feats = extract(rng.normal(0, 0.3, RATE), RATE)
    assert not feats.is_reliable


def test_무음은_측정_불가로_돌려준다():
    feats = extract(np.zeros(RATE), RATE)
    assert feats.voiced_ratio == 0.0
    assert math.isnan(feats.f0_median_hz)


# ── 옥타브 보정 — 2026-09-09 실측으로 필요해진 것 ────────────────────────
def test_옥타브_오류를_되돌린다():
    """8kHz 에서 자기상관이 2배 배음에 걸리는 일이 잦다. 보정 없이 재니 발화 하나 안의
    F0 폭이 100Hz 로 나왔다 — 억양이 아니라 **추정기 오류를 잰 것**이었다."""
    f0 = np.array([180.0, 180.0, 360.0, 180.0, 90.0, 180.0])
    fixed = _fix_octave_errors(f0)
    assert np.allclose(fixed, 180.0)


def test_애매한_값은_되돌리지_않고_그대로_둔다():
    """275Hz 를 137.5 로 스냅하면 **진짜 억양을 지운 것**일 수 있다. 우리가 재려는 것이
    억양 폭이라 측정 도구가 측정 대상을 깎게 된다(절대 원칙 10).

    첫 판에서 실제로 그랬다 — 「기준 대비 1.6배 창」이 옥타브 간격보다 넓어서 어떤
    값이든 ×2 나 ÷2 중 하나가 창 안에 들어왔고, 거의 모든 값이 스냅됐다."""
    f0 = np.array([180.0, 180.0, 180.0, 181.0, 275.0])
    fixed = _fix_octave_errors(f0)
    assert fixed[4] == 275.0


def test_F0_범위_밖은_버린다():
    """되돌려도 사람 목소리 범위에 못 들어오는 값은 잡음이다."""
    f0 = np.array([180.0, 180.0, 180.0, 900.0])
    assert math.isnan(_fix_octave_errors(f0)[3])


def test_보정이_흔들림을_줄인다():
    """같은 신호를 보정 전후로 비교한다 — 보정이 실제로 폭을 좁히는지."""
    clean = np.array([180.0] * 10)
    noisy = np.array([180.0] * 7 + [360.0, 90.0, 360.0])
    assert np.nanstd(_fix_octave_errors(noisy)) < np.nanstd(noisy)
    assert np.allclose(_fix_octave_errors(clean), clean)


# ── 에너지 ───────────────────────────────────────────────────────────────
def test_큰_소리가_더_높은_dB_로_나온다():
    quiet = extract(tone(180.0) * 0.1, RATE)
    loud = extract(tone(180.0) * 1.0, RATE)
    assert loud.energy_median_db > quiet.energy_median_db


def test_앞뒤_침묵은_에너지_중앙값을_끌어내리지_않는다():
    """통화 녹음은 앞뒤에 침묵이 붙는다. 섞어 재면 「말이 없었다」가
    「조용히 말했다」로 기록된다."""
    speech = tone(180.0, seconds=1.0)
    padded = np.concatenate([np.zeros(RATE), speech, np.zeros(RATE)])
    assert abs(extract(padded, RATE).energy_median_db
               - extract(speech, RATE).energy_median_db) < 1.0


def test_표본율이_0이면_거부한다():
    with pytest.raises(ValueError):
        extract(np.zeros(10), 0)
