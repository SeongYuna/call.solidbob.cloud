# Requirement: 7.3절 전사 이벤트
"""통화 시작 인터랙터 — 시각을 채우고 기록 포트에 넘긴다. 판정은 없다."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from hub.app.dtos.call_start_dto import CallStartCommand, CallStarted
from hub.app.ports.input.call_start_use_case import CallStartUseCase
from hub.app.ports.output.call_start_record_port import CallStartRecordPort

# db/schema.sql `call.status` 는 자유 문자열이다. 통화 후 처리(D)가 붙으면 그쪽이 값을 바꾼다.
_STATUS_IN_PROGRESS = "in_progress"


class CallStartInteractor(CallStartUseCase):
    def __init__(self, record: CallStartRecordPort) -> None:
        self._record = record

    async def start(self, command: CallStartCommand) -> CallStarted:
        call = CallStarted(
            call_id=command.call_id,
            domain=command.domain,
            stt_engine=command.stt_engine,
            channel_count=command.channel_count,
            started_at=command.started_at or datetime.now(timezone.utc),
            status=_STATUS_IN_PROGRESS,
            created=True,
        )
        created = await self._record.record(call)
        return call if created else replace(call, created=False)
