# Requirement: B-5, D-1, F-2
"""통화 기록 조회 인터랙터. 입력 검사와 «없음» 을 예외로 바꾸는 것이 전부다 — 정렬·가공은 리포지토리 몫이다."""

from __future__ import annotations

from dataclasses import replace

from hub.app.dtos.call_record_dto import CallRecord, CallRecordNotFound
from hub.app.ports.input.call_record_use_case import CallRecordUseCase
from hub.app.ports.output.call_record_port import CallRecordPort
from hub.app.ports.output.closure_gate_port import ClosureGatePort


class CallRecordInteractor(CallRecordUseCase):
    def __init__(self, record_port: CallRecordPort, gate: ClosureGatePort | None = None) -> None:
        self._records = record_port
        self._gate = gate

    async def get(self, call_id: str) -> CallRecord:
        if not call_id.strip():
            raise ValueError("call_id 가 비어 있습니다")
        record = await self._records.get(call_id)
        if record is None:
            raise CallRecordNotFound(f"통화가 없습니다: {call_id}")
        if self._gate is None or not record.closures:
            return record
        # 절차 제목은 저장하지 않고 규칙표에서 붙인다(2026-10-01) — 화면이 `DASAN-TERM-4.3` 대신 「주민등록초본 발급」을 보인다.
        # 규칙표에 없는 절차는 None 그대로 — 제목을 지어내지 않는다
        return replace(record, closures=tuple(
            replace(cl, procedure_title=self._gate.title_of(cl.procedure)) if cl.procedure_title is None else cl
            for cl in record.closures
        ))
