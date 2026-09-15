# Requirement: B-5, D-1, F-2
"""통화 기록 조회 인터랙터. 입력 검사와 «없음» 을 예외로 바꾸는 것이 전부다 — 정렬·가공은 리포지토리 몫이다."""

from __future__ import annotations

from hub.app.dtos.call_record_dto import CallRecord, CallRecordNotFound
from hub.app.ports.input.call_record_use_case import CallRecordUseCase
from hub.app.ports.output.call_record_port import CallRecordPort


class CallRecordInteractor(CallRecordUseCase):
    def __init__(self, record_port: CallRecordPort) -> None:
        self._records = record_port

    async def get(self, call_id: str) -> CallRecord:
        if not call_id.strip():
            raise ValueError("call_id 가 비어 있습니다")
        record = await self._records.get(call_id)
        if record is None:
            raise CallRecordNotFound(f"통화가 없습니다: {call_id}")
        return record
