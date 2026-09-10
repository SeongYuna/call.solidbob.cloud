# Requirement: 7.3절 전사 이벤트
"""PostgreSQL 설정이 없을 때의 로그 구현. 전사 기록도 같은 조건에서 로그로 떨어지므로 짝이 맞는다."""

from __future__ import annotations

import logging

from hub.app.dtos.call_start_dto import CallStarted
from hub.app.ports.output.call_start_record_port import CallStartRecordPort

logger = logging.getLogger(__name__)


class LogCallStartRecordAdapter(CallStartRecordPort):
    async def record(self, call: CallStarted) -> bool:
        logger.info(
            "call started call_id=%s domain=%s stt_engine=%s channel_count=%d started_at=%s",
            call.call_id, call.domain, call.stt_engine, call.channel_count, call.started_at.isoformat(),
        )
        return True
