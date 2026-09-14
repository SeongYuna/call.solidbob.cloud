# Requirement: F-2
"""자동 판정 인터랙터 — 탐지 포트로 서류별 안내 여부를 얻고, 게이트로 판정하고, 남긴다. 판정은 둘 다 포트 뒤 규칙이 한다.

결과의 `detected=True` 는 «사람이 체크한 것이 아니라 키워드로 본 것» 이라는 표시다 — 화면과 기록이 둘을 구분한다.
"""

from __future__ import annotations

from dataclasses import replace

from hub.app.dtos.closure_verdict_dto import ClosureVerdict
from hub.app.dtos.required_docs_detection_dto import RequiredDocsDetectionCommand
from hub.app.ports.input.required_docs_detection_use_case import RequiredDocsDetectionUseCase
from hub.app.ports.output.closure_gate_port import ClosureGatePort
from hub.app.ports.output.closure_record_port import ClosureRecordPort
from hub.app.ports.output.required_docs_detection_port import RequiredDocsDetectionPort


class RequiredDocsDetectionInteractor(RequiredDocsDetectionUseCase):
    def __init__(
        self, detection: RequiredDocsDetectionPort, closure_gate: ClosureGatePort, record: ClosureRecordPort
    ) -> None:
        self._detection = detection
        self._closure_gate = closure_gate
        self._record = record

    async def check(self, command: RequiredDocsDetectionCommand) -> ClosureVerdict:
        if not command.procedure:
            raise ValueError("절차가 비어 있습니다")
        evidence = self._detection.detect(command.procedure, command.agent_utterances)
        verdict = replace(
            self._closure_gate.evaluate(call_id=command.call_id, procedure=command.procedure, evidence=evidence),
            detected=True,
        )
        await self._record.record(verdict)
        return verdict
