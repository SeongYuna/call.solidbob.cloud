# Requirement: D-5
"""`VoiceOutlierPort` 구현 — 발화별 WAV 를 읽어 톤 특징을 뽑고, 화자 자신의 기준선 대비 튄 발화를 고른다.

여기가 adapter 인 이유: 파일 I/O(`wav_reader`)를 하고 hub 의 DTO·포트를 아는 코드이기 때문이다.
판정은 `domain/services/outlier.py`, 특징 추출은 `domain/services/features.py` 에 있고 이 파일은
**이어 붙이고 형태를 바꾸기만 한다**(`.importlinter` 계약 1). 순서는 `scripts/measure_call_temperature.py`
가설 3 과 같다 —

```
(segment_id, 경로)  ─read_mono─▶  샘플  ─extract─▶  VoiceFeatures  ─f0_median_hz─▶  segment_outliers
```

특징값으로 **F0 중앙값**을 쓴다. 측정 스크립트가 시나리오 안 이상 구간을 셀 때 쓴 축 그대로이고,
`voiced_ratio` 가 낮아 믿을 수 없는 발화(`VoiceFeatures.is_reliable` False)와 F0 가 안 잡힌 발화는
**nan 으로 넘긴다** — 도메인이 nan 을 기준선·판정 양쪽에서 빼므로(`build_baseline`·`deviations`) 여기서
따로 거르지 않는다. 그 발화는 「튀지 않았다」가 아니라 「값이 없다」다.

⚠ **파일이 없거나 못 읽으면 예외를 그대로 올린다.** 빈 값으로 갈아끼우면 기준선이 남은 발화로 조용히
만들어지고, 골든셋의 라벨은 그 발화를 여전히 가리킨다 — 판정을 지어내는 셈이다(절대 원칙 10).

⚠ **기준선을 못 만들면 `judged=False`** — 발화 8건 미만·척도 0 등은 도메인(`Baseline.usable`)이 정한 그대로다.
빈 `outliers` 를 「튄 구간 없음」으로 세지 않는다. 오디오는 판정 뒤 보관하지 않는다(절대 원칙 7) —
이 어댑터는 경로만 받고 아무것도 쓰지 않는다.

파일을 읽는 동기 I/O 를 이벤트 루프에서 그대로 한다. 발화 클립은 수 초짜리라 짧고, 지금 부르는 곳은
평가 하네스뿐이다 — 실시간 경로가 생기면 그때 스레드로 뺀다.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from hub.app.dtos.transcript_dto import Speaker
from hub.app.dtos.voice_outlier_dto import VoiceOutlier, VoiceOutlierVerdict
from hub.app.ports.output.voice_outlier_port import VoiceOutlierPort

from ...domain.services.features import extract
from ...domain.services.outlier import segment_outliers
from .wav_reader import read_mono


def utterance_feature(path: Path) -> float:
    """발화 오디오 하나 → 기준선에 넣을 특징값(F0 중앙값 Hz). 믿을 수 없으면 nan."""
    samples, rate = read_mono(path)
    features = extract(samples, rate)
    if not features.is_reliable:
        return float("nan")
    return features.f0_median_hz  # F0 를 못 잡았으면 이미 nan 이다


class WavVoiceOutlierAdapter(VoiceOutlierPort):
    """WAV 파일 경로 기반 v1. 콜 미디에이터가 특징값을 직접 실어 보내게 되면 그쪽 어댑터를 따로 둔다."""

    async def judge(
        self, call_id: str, speaker: Speaker, utterances: Sequence[tuple[int, str]]
    ) -> VoiceOutlierVerdict:
        samples = [(segment_id, utterance_feature(Path(path))) for segment_id, path in utterances]
        result = segment_outliers(speaker, samples)
        if not result.baseline_usable:
            return VoiceOutlierVerdict(call_id=call_id, speaker=speaker, judged=False)
        return VoiceOutlierVerdict(
            call_id=call_id,
            speaker=speaker,
            judged=True,
            outliers=tuple(
                VoiceOutlier(
                    segment_id=o.segment_id, speaker=speaker, robust_z=o.robust_z, baseline_n=o.baseline_n
                )
                for o in result.outliers
            ),
        )
