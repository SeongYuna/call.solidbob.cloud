# Requirement: F-2
"""필요서류 체크리스트 인터랙터(호출자가 체크리스트를 채운 경우). 게이트를 부르고 판정을 남긴다.

**여기서 절대 하지 않는 것**:
- `evidence` 값을 보고 스스로 complete/incomplete 를 정하지 않는다. 규칙표는 closure_gate 스포크의 도메인이 갖는다.
- 판정을 생성 모델에 맡기지 않는다(절대 원칙 9). 설명(reason)만 나른다.
- 스포크가 없을 때 "일단 통과"시키지 않는다 — 그 순간 F-2 의 존재 이유가 사라진다.
"""

from __future__ import annotations

from hub.app.dtos.closure_dto import ClosureCheckCommand
from hub.app.dtos.closure_verdict_dto import ClosureVerdict
from hub.app.ports.input.closure_check_use_case import ClosureCheckUseCase
from hub.app.ports.output.closure_gate_port import ClosureGatePort
from hub.app.ports.output.closure_record_port import ClosureRecordPort


class ClosureCheckInteractor(ClosureCheckUseCase):
    def __init__(self, closure_gate: ClosureGatePort, record: ClosureRecordPort | None = None) -> None:
        self._closure_gate = closure_gate
        self._record = record

    async def check(self, command: ClosureCheckCommand) -> ClosureVerdict:
        if not command.procedure:
            raise ValueError("절차가 비어 있습니다")
        if not command.evidence:
            raise ValueError("근거 필드가 비어 있습니다 — 빈 근거로는 체크리스트를 판정할 수 없습니다")

        verdict = self._closure_gate.evaluate(
            call_id=command.call_id,
            procedure=command.procedure,
            evidence=dict(command.evidence),
            reason=command.reason,
        )
        if self._record is not None:
            await self._record.record(verdict)
        return verdict
