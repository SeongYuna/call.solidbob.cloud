# Requirement: D-5, QUA-1
"""오디오 경로 → 판정 어댑터. **합성 톤으로 검증한다** — 정답 F0 를 우리가 정하므로 어느 발화가 튀어야
하는지 말할 수 있다(`test_features.py` 와 같은 이유). 판정 자체는 도메인 함수 결과와 같아야 하고,
기준선을 못 만든 것과 파일을 못 읽은 것을 「튄 구간 없음」과 섞지 않는다(절대 원칙 10)."""

from __future__ import annotations

import asyncio
import math
import wave
from pathlib import Path

import numpy as np
import pytest

from voice_signal.adapter.outbound.wav_voice_outlier_adapter import WavVoiceOutlierAdapter, utterance_feature
from voice_signal.domain.services.outlier import MIN_BASELINE_UTTERANCES, segment_outliers

RATE = 8000  # 전화망 표준


def _tone(f0: float, seconds: float = 1.0, harmonics: int = 4) -> np.ndarray:
    t = np.arange(int(RATE * seconds)) / RATE
    signal = sum(np.sin(2 * math.pi * f0 * k * t) / k for k in range(1, harmonics + 1))
    return signal / np.abs(signal).max() * 0.8


def _write_wav(path: Path, samples: np.ndarray) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((samples * 32767).astype(np.int16).tobytes())
    return path


def _calls(tmp_path: Path, f0s: dict[int, float]) -> list[tuple[int, str]]:
    return [(sid, str(_write_wav(tmp_path / f"u{sid:02d}.wav", _tone(f0)))) for sid, f0 in f0s.items()]


def test_튄_발화를_segment_id_로_돌려주고_도메인_판정과_같다(tmp_path):
    # 기준선 15건은 176~190Hz 근처, 한 건(segment 40)만 380Hz
    f0s = {sid: 176.0 + sid for sid in range(1, 16)} | {40: 380.0}
    utterances = _calls(tmp_path, f0s)

    verdict = asyncio.run(WavVoiceOutlierAdapter().judge("c_001", "customer", utterances))

    assert verdict.judged is True
    assert [(o.segment_id, o.speaker, o.baseline_n) for o in verdict.outliers] == [(40, "customer", 16)]
    # 어댑터는 이어 붙이기만 한다 — 같은 파일을 도메인 함수에 직접 넣은 결과와 한 글자도 다르지 않아야 한다
    expected = segment_outliers("customer", [(sid, utterance_feature(Path(p))) for sid, p in utterances])
    assert [(o.segment_id, o.robust_z, o.baseline_n) for o in verdict.outliers] == [
        (o.segment_id, o.robust_z, o.baseline_n) for o in expected.outliers
    ]


def test_튄_구간이_없어도_판정했으면_judged_는_True_다(tmp_path):
    utterances = _calls(tmp_path, {sid: 176.0 + sid for sid in range(1, 13)})
    verdict = asyncio.run(WavVoiceOutlierAdapter().judge("c_001", "agent", utterances))
    assert verdict.judged is True
    assert verdict.outliers == ()


def test_발화_수가_부족하면_판정하지_않는다(tmp_path):
    utterances = _calls(tmp_path, {sid: 180.0 for sid in range(MIN_BASELINE_UTTERANCES - 1)})
    verdict = asyncio.run(WavVoiceOutlierAdapter().judge("c_001", "customer", utterances))
    assert verdict.judged is False
    assert verdict.outliers == ()


def test_무음_발화는_값이_없어_기준선에서_빠진다(tmp_path):
    """무음은 「튀지 않음」이 아니라 「값 없음」이다 — 기준선 n 에 들어가지 않고 판정 대상도 아니다."""
    utterances = _calls(tmp_path, {sid: 176.0 + sid for sid in range(1, 9)} | {50: 380.0})
    utterances.append((60, str(_write_wav(tmp_path / "silent.wav", np.zeros(RATE)))))
    verdict = asyncio.run(WavVoiceOutlierAdapter().judge("c_001", "customer", utterances))
    assert verdict.judged is True
    assert [(o.segment_id, o.baseline_n) for o in verdict.outliers] == [(50, 9)]


def test_없는_파일은_예외를_올린다(tmp_path):
    """빈 값으로 갈아끼우면 남은 발화로 기준선이 조용히 만들어진다 — 판정을 지어내지 않는다."""
    utterances = _calls(tmp_path, {sid: 180.0 for sid in range(1, 10)})
    utterances.append((99, str(tmp_path / "missing.wav")))
    with pytest.raises(FileNotFoundError):
        asyncio.run(WavVoiceOutlierAdapter().judge("c_001", "customer", utterances))
