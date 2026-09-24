# Requirement: 7.3절 전사 이벤트
"""통화 시작 인터랙터 — 시각을 채우고, 발신 번호가 있으면 고객 식별자로 바꿔 기록 포트에 넘긴다. 판정은 없다.

발신 번호(평문)는 이 함수 안에서 `CustomerRefPort` 로 바뀌고 사라진다 — `CallStarted` 에는 식별자만 실린다(SEC-1).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from hub.app.dtos.call_start_dto import CallStartCommand, CallStarted
from hub.app.ports.input.call_start_use_case import CallStartUseCase
from hub.app.ports.output.call_start_record_port import CallStartRecordPort
from hub.app.ports.output.customer_ref_port import CustomerRefPort

# db/schema.sql `call.status` 는 자유 문자열이다. 통화 후 처리(D)가 붙으면 그쪽이 값을 바꾼다.
_STATUS_IN_PROGRESS = "in_progress"


class CallStartInteractor(CallStartUseCase):
    def __init__(self, record: CallStartRecordPort, customer_ref: CustomerRefPort | None = None) -> None:
        self._record = record
        self._customer_ref = customer_ref

    async def start(self, command: CallStartCommand) -> CallStarted:
        customer_id = None
        if command.caller_phone and self._customer_ref is not None:
            customer_id = self._customer_ref.ref(command.caller_phone)  # 형식이 틀리면 InvalidPhoneNumber
        call = CallStarted(
            call_id=command.call_id,
            domain=command.domain,
            stt_engine=command.stt_engine,
            channel_count=command.channel_count,
            started_at=command.started_at or datetime.now(timezone.utc),
            status=_STATUS_IN_PROGRESS,
            created=True,
            customer_id=customer_id,
        )
        created = await self._record.record(call)
        if created:
            return call
        # 다시 연 통화 — 발화 번호를 이어 세도록 저장된 마지막 번호를 알려 준다(`w6-segment-id-reuse`)
        return replace(call, created=False, last_segment_id=await self._record.last_segment_id(command.call_id))
