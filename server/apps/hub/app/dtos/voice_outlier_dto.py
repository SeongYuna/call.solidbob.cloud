# Requirement: D-5
from __future__ import annotations

from dataclasses import dataclass

from .transcript_dto import Speaker


@dataclass(frozen=True)
class VoiceOutlier:
    """D-5 통화 온도 — 화자 자신의 기준선에서 튄 발화 1건(`decisions/203`).

    ⚠ **`robust_z` 는 저장용이다. 화면으로 내보내는 응답에 싣지 않는다**([부록 A-1](/docs/12/)).
    저장하는 이유는 임계값 3.5 가 **재서 고른 값이 아니라** 나중에 바꿔 재판정해야 하기 때문이다 —
    오디오를 보관하지 않으므로(절대 원칙 7) 이 값이 없으면 재판정 자체가 불가능하다.
    화면이 쓰는 것은 **구간 수**다(`blacklist_request.temperature_outliers`).
    """

    segment_id: int
    speaker: Speaker
    robust_z: float
    baseline_n: int  # 기준선을 만든 발화 수 — 8 미만이면 애초에 판정하지 않는다

    def __post_init__(self) -> None:
        if self.speaker not in ("customer", "agent"):
            raise ValueError(f"'{self.speaker}' 는 화자가 아닙니다 (customer | agent)")
        if self.baseline_n < 1:
            raise ValueError("baseline_n 은 1 이상이어야 합니다 — 기준선 없이 판정한 이상 구간은 없다")
