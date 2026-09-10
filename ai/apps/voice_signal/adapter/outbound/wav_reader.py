# Requirement: D-5
"""WAV 파일 → 모노 float 배열. 파일 I/O 라서 adapter 계층이다(`.importlinter` 계약 1).

표준 라이브러리 `wave` 만 쓴다. `soundfile`·`librosa` 를 들이지 않는 이유: 우리가 읽는
것은 **16bit PCM 모노/스테레오 하나뿐**이고(다산콜DB 8kHz/2ch · 저품질전화 8kHz/1ch ·
krespspeech 16kHz/1ch), 그 하나 때문에 네이티브 의존성을 추가하면 CI 와 도커 이미지가
같이 무거워진다.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

# 16bit PCM 의 최대값. 이걸로 나눠 -1~1 로 맞춘다.
_INT16_SCALE = 32768.0


def read_mono(path: Path) -> tuple[np.ndarray, int]:
    """(-1~1 float 배열, 표본율)을 돌려준다.

    **스테레오는 평균으로 합친다.** 다산콜DB 가 2채널인데 두 채널이 서로 다르다(확인함).
    채널이 화자를 나누는지 아니면 같은 소리의 두 마이크인지는 `w1-v1-channel` 이
    확인한 범위 밖이라, **여기서 화자 분리를 가정하지 않는다** — 가정하면 틀렸을 때
    조용히 잘못된 기준선이 만들어진다. 화자는 파일명이나 A-2(화자 분리)가 준다.
    """
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError(f"16bit PCM 만 읽는다: {path} ({w.getsampwidth() * 8}bit)")
        rate = w.getframerate()
        channels = w.getnchannels()
        raw = w.readframes(w.getnframes())

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / _INT16_SCALE
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, rate
