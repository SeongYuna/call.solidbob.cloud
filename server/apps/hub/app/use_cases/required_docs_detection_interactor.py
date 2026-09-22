# Requirement: F-2
"""자동 판정 인터랙터 — 탐지 포트로 서류별 안내 여부를 얻고, 게이트로 판정하고, 남긴다. 판정은 둘 다 포트 뒤 규칙이 한다.

결과의 `detected=True` 는 «사람이 체크한 것이 아니라 키워드로 본 것» 이라는 표시다 — 화면과 기록이 둘을 구분한다.
"""

from __future__ import annotations

import logging
from dataclasses import replace

from hub.app.dtos.closure_verdict_dto import ClosureVerdict
from hub.app.dtos.required_docs_detection_dto import RequiredDocsDetectionCommand
from hub.app.ports.input.required_docs_detection_use_case import RequiredDocsDetectionUseCase
from hub.app.ports.output.closure_gate_port import ClosureGatePort
from hub.app.ports.output.closure_record_port import ClosureRecordPort
from hub.app.ports.output.required_docs_detection_port import RequiredDocsDetectionPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

logger = logging.getLogger(__name__)


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
        await _record_or_log(self._record, verdict)
        return verdict


async def _record_or_log(record: ClosureRecordPort, verdict: ClosureVerdict) -> None:
    # 기록이 실패해도 **판정은 돌려준다**(`decisions/318` — 콜 가드·컴플라이언스와 같은 규칙). 화면에 나가는 결과가
    # 기록 실패(우리 쪽 DB 흔들림) 때문에 사라지지 않게 한다. 삼키지 않는 것: 통화가 없다(호출자 실수 — 404).
    try:
        await record.record(verdict)
    except CallNotStartedError:
        raise
    except Exception as exc:  # noqa: BLE001 — 우리 쪽 사정은 응답을 막지 않는다
        logger.warning("closure verdict not stored call_id=%s procedure=%s verdict=%s reason=%s",
                       verdict.call_id, verdict.procedure, verdict.verdict, type(exc).__name__)
