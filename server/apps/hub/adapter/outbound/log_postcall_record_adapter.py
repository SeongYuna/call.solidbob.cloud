# Requirement: D-1, D-2, D-3
"""PostgreSQL 이 없을 때의 통화 후 초안 기록. 요약 본문은 남기지 않는다 — 마스킹본이어도 로그에 통화 내용을 쌓지 않는다."""

from __future__ import annotations

import logging

from hub.app.dtos.call_summary_dto import CallSummaryDraft
from hub.app.ports.output.postcall_record_port import PostcallRecordPort

logger = logging.getLogger(__name__)


class LogPostcallRecordAdapter(PostcallRecordPort):
    async def record(self, draft: CallSummaryDraft) -> None:
        logger.info(
            "postcall draft call_id=%s summary_chars=%d inquiry_type=%s follow_ups=%d",
            draft.call_id, len(draft.summary_text), draft.inquiry_type, len(draft.follow_up_actions),
        )
