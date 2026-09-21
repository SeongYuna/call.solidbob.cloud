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


@dataclass(frozen=True)
class VoiceOutlierVerdict:
    """`VoiceOutlierPort.judge` 의 결과 — 한 통화·한 화자의 판정.

    `judged` 가 False 면 기준선을 못 만든 것이다(발화 8건 미만 등). 그때 `outliers` 는 비어 있지만
    **「튄 구간 없음」이 아니라 「판정하지 않았다」다**(절대 원칙 10) — 두 상태를 하나로 뭉치지 않으려고
    불리언을 따로 둔다. 판정하지 않았는데 이상 구간이 있으면 모순이라 거부한다.
    """

    call_id: str
    speaker: Speaker
    judged: bool
    outliers: tuple[VoiceOutlier, ...] = ()

    def __post_init__(self) -> None:
        if self.speaker not in ("customer", "agent"):
            raise ValueError(f"'{self.speaker}' 는 화자가 아닙니다 (customer | agent)")
        if not self.judged and self.outliers:
            raise ValueError("판정하지 않았는데 이상 구간이 있다 — judged=False 면 outliers 는 비어 있어야 한다")

