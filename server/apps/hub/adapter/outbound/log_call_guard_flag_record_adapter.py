# Requirement: C-6, SEC-1
"""PostgreSQL 이 없을 때의 기록 구현. 갈래·위치만 남긴다 — 잡힌 표현(`phrase`)도 로그에 싣지 않는다.

`phrase` 는 마스킹된 본문에서 잘랐지만 고객이 한 말 그대로다. 로그는 DB 보다 오래·넓게 퍼지므로 싣지 않는다.
"""

from __future__ import annotations

import logging

from hub.app.dtos.call_guard_dto import CallGuardFlag
from hub.app.ports.output.call_guard_flag_record_port import CallGuardFlagRecordPort

logger = logging.getLogger(__name__)


class LogCallGuardFlagRecordAdapter(CallGuardFlagRecordPort):
    async def record(self, call_id: str, segment_id: int, flags: tuple[CallGuardFlag, ...]) -> None:
        logger.info(
            "call guard flagged call_id=%s segment_id=%s categories=%s",
            call_id, segment_id, ",".join(f.category for f in flags),
        )
