# Requirement: C-1, C-2, C-3, C-4, D-4
"""컴플라이언스 검사 인터랙터. CompliancePort 를 부르고, 잡힌 것이 있으면 기록 포트에 남기고, 결과를 감싼다.

**여기서 하지 않는 것**:
- 발견 건수로 등급·점수를 만들지 않는다 (부록 A-1 — "위험도 78%" 금지).
- 애매한 건을 걸러내지 않는다. 재현율 우선이라 판단은 스포크가 하고 허브는 나른다.
- 고객 발화를 검사하지 않는다 — 커맨드가 `agent_utterance` 만 받는 이유다.
- **저장 실패로 응답을 막지 않는다.** 화면 경고가 먼저다 — 전사가 아직 없거나(외래키) DB 가 죽어도 잡힌 위반은
  응답으로 나가고, 저장 실패는 로그에 남는다(2026-09-18 — 그전에는 아예 저장하지 않아 `compliance_flag` 가 늘 비었다).
"""

from __future__ import annotations

import logging

from hub.app.dtos.compliance_dto import ComplianceCheckCommand, ComplianceCheckResult
from hub.app.ports.input.compliance_check_use_case import ComplianceCheckUseCase
from hub.app.ports.output.compliance_flag_record_port import ComplianceFlagRecordPort
from hub.app.ports.output.compliance_port import CompliancePort
from hub.app.ports.output.transcript_ingest_record_port import SegmentNotFoundError

logger = logging.getLogger(__name__)


class ComplianceCheckInteractor(ComplianceCheckUseCase):
    def __init__(self, compliance: CompliancePort, record: ComplianceFlagRecordPort) -> None:
        self._compliance = compliance
        self._record = record

    async def check(self, command: ComplianceCheckCommand) -> ComplianceCheckResult:
        utterance = command.agent_utterance.strip()
        if not utterance:
            raise ValueError("상담원 발화가 비어 있습니다")

        findings = tuple(await self._compliance.detect(utterance))
        if findings:
            try:
                await self._record.record(command.call_id, command.segment_id, findings)
            except SegmentNotFoundError:
                # **호출자의 순서 실수**는 삼키지 않는다(2026-09-20). 삼키면 응답이 200 이라 「저장된 줄 알았는데
                # 0행」이 조용히 이어진다 — 운영 왕복에서 실제로 그랬다. 라우터가 404 로 돌려준다.
                # 아래의 «어떤 실패든 막지 않는다»는 **우리 쪽 사정(DB 흔들림)** 에만 해당한다
                raise
            except Exception as exc:  # noqa: BLE001 — 저장은 응답 뒤의 일이다. 우리 쪽 실패는 응답을 막지 않는다
                logger.warning(
                    "compliance flag not stored call_id=%s segment_id=%s rules=%s reason=%s",
                    command.call_id, command.segment_id, ",".join(f.rule_code for f in findings),
                    type(exc).__name__,
                )
        return ComplianceCheckResult(
            call_id=command.call_id,
            segment_id=command.segment_id,
            findings=findings,
        )
