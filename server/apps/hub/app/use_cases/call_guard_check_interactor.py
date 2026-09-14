# Requirement: C-6
"""콜 가드 검사 인터랙터 — CallGuardPort 로 찾고, 잡힌 것이 있으면 기록 포트에 남긴다.

**여기서 하지 않는 것**:
- 건수로 등급·점수를 만들지 않는다 (부록 A-1 — "위험도 78%" 금지).
- 통화를 끊을지·상급자를 부를지 정하지 않는다 — `DASAN-MANUAL-5.2` 가 최종 판단을 사람에게 둔다.
- 애매한 건을 걸러내지 않는다. 재현율 우선이라 판단은 스포크가 하고 허브는 나른다.
- 상담원 발화를 검사하지 않는다 — 커맨드가 `customer_utterance` 만 받는 이유다.
"""

from __future__ import annotations

from hub.app.dtos.call_guard_check_dto import CallGuardCheckCommand, CallGuardCheckResult
from hub.app.ports.input.call_guard_check_use_case import CallGuardCheckUseCase
from hub.app.ports.output.call_guard_flag_record_port import CallGuardFlagRecordPort
from hub.app.ports.output.call_guard_port import CallGuardPort


class CallGuardCheckInteractor(CallGuardCheckUseCase):
    def __init__(self, call_guard: CallGuardPort, record: CallGuardFlagRecordPort) -> None:
        self._call_guard = call_guard
        self._record = record

    async def check(self, command: CallGuardCheckCommand) -> CallGuardCheckResult:
        utterance = command.customer_utterance
        if not utterance.strip():
            raise ValueError("고객 발화가 비어 있습니다")

        # 공백을 잘라 넘기지 않는다 — 스포크가 돌려준 span 이 받은 문자열 기준이어야 화면 자막과 맞는다.
        flags = tuple(await self._call_guard.detect(utterance))
        if flags:
            await self._record.record(command.call_id, command.segment_id, flags)
        return CallGuardCheckResult(call_id=command.call_id, segment_id=command.segment_id, flags=flags)
