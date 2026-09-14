# Requirement: F-2
"""PostgreSQL 이 없을 때의 판정 기록. 절차·판정·누락 건수만 남긴다."""

from __future__ import annotations

import logging

from hub.app.dtos.closure_verdict_dto import ClosureVerdict
from hub.app.ports.output.closure_record_port import ClosureRecordPort

logger = logging.getLogger(__name__)


class LogClosureRecordAdapter(ClosureRecordPort):
    async def record(self, verdict: ClosureVerdict) -> None:
        logger.info(
            "closure checked call_id=%s procedure=%s verdict=%s missing=%d detected=%s",
            verdict.call_id, verdict.procedure, verdict.verdict, len(verdict.missing), verdict.detected,
        )
