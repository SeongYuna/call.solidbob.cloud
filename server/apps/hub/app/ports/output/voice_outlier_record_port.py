# Requirement: D-5
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from hub.app.dtos.transcript_dto import Speaker
from hub.app.dtos.voice_outlier_dto import VoiceOutlier


class VoiceOutlierRecordPort(ABC):
    """D-5 이상 구간을 남긴다(`voice_outlier`). **통화가 끝나면 재계산이 불가능하다** —
    오디오를 보관하지 않기 때문이다(절대 원칙 7).

    **화자 단위로 갈아끼운다(`replace`).** 기준선은 그 화자의 발화 전체로 만들어지므로 발화가
    늘면 앞 발화의 판정도 바뀐다 — 한 건씩 덧붙이면 옛 기준선의 판정과 새 기준선의 판정이 섞인다.

    ⚠ **기준선을 못 만들었으면(`baseline.usable` 이 False) 부르지 않는다.** 빈 목록으로
    `replace` 하면 「튄 구간이 없다」로 기록되는데, 실제로는 「판정하지 않았다」다(절대 원칙 10).
    """

    @abstractmethod
    async def replace(self, call_id: str, speaker: Speaker, outliers: Sequence[VoiceOutlier]) -> None: ...
