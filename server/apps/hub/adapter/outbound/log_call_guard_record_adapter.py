# Requirement: C-6
"""DB 없이 도는 경로의 콜 가드 기록. **걸린 표현(`phrase`)을 로그에 싣지 않는다** — 갈래와 건수만.

마스킹된 자막에서 잘라낸 것이라 개인정보는 없지만, 로그는 보존 기간·접근 통제가 DB 보다 느슨하다.
관리자가 볼 근거는 `call_guard_flag` 에 남기고, 로그는 「돌았다」만 증명한다.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from hub.app.dtos.call_guard_dto import CallGuardFlag
from hub.app.ports.output.call_guard_record_port import CallGuardRecordPort

logger = logging.getLogger(__name__)


class LogCallGuardRecordAdapter(CallGuardRecordPort):
    async def replace(self, call_id: str, segment_id: int, flags: Sequence[CallGuardFlag]) -> None:
        logger.info(
            "call_guard call_id=%s segment_id=%s categories=%s",
            call_id, segment_id, ",".join(f.category for f in flags) or "-",
        )
