# Requirement: C-6
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from hub.app.dtos.call_guard_dto import CallGuardFlag


class CallGuardRecordPort(ABC):
    """C-6 탐지 결과를 남긴다(`call_guard_flag`). 저장하지 않으면 관리자가 「폭언 3건」을
    **어느 발화가 걸렸는지** 확인할 방법이 없다(`decisions/204` 「통화를 다시 듣지 않고 판단」).

    **발화 단위로 갈아끼운다(`replace`).** 게이트웨이가 같은 확정 발화를 다시 보내면
    `transcript_segment` 는 UPSERT 로 텍스트가 바뀐다 — 그때 옛 탐지가 남아 있으면 지금 자막에
    없는 표현이 기록에 남는다. `masking_event` 를 지우고 다시 넣는 것과 같은 이유다.
    **빈 목록도 호출한다** — 「이제 걸린 것이 없다」도 갱신이다.

    ⚠ `flags` 의 `phrase`·구간은 **마스킹된 자막 기준**이어야 한다(`DASAN-MANUAL-5.5`).
    이 포트는 받은 것을 그대로 쓴다 — 순서는 인터랙터가 보장한다.
    """

    @abstractmethod
    async def replace(self, call_id: str, segment_id: int, flags: Sequence[CallGuardFlag]) -> None: ...
