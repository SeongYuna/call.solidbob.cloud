# Requirement: C-1, C-2, C-3, C-4, SEC-1
"""PostgreSQL 이 없을 때의 기록 구현. 코드만 남긴다 — 잡힌 표현(`phrase`)은 로그에 싣지 않는다.

`phrase` 는 마스킹된 본문에서 잘랐지만 상담원이 한 말 그대로다. 로그는 DB 보다 오래·넓게 퍼지므로 싣지 않는다
(콜 가드 로그 어댑터와 같은 이유).
"""

from __future__ import annotations

import logging

from hub.app.dtos.compliance_finding_dto import ComplianceFinding
from hub.app.ports.output.compliance_flag_record_port import ComplianceFlagRecordPort

logger = logging.getLogger(__name__)


class LogComplianceFlagRecordAdapter(ComplianceFlagRecordPort):
    async def record(self, call_id: str, segment_id: int, findings: tuple[ComplianceFinding, ...]) -> None:
        logger.info(
            "compliance flagged call_id=%s segment_id=%s rules=%s",
            call_id, segment_id, ",".join(f.rule_code for f in findings),
        )
