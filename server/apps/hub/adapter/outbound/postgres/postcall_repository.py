# Requirement: D-1, D-2, D-3, SEC-1
"""PostcallRecordPort 의 PostgreSQL 구현 — `call` 요약 칸 갱신 + `follow_up_action` 초안 교체를 한 트랜잭션에.

**확정된 요약은 덮지 않는다.** `summary_confirmed_at` 을 행 잠금으로 먼저 읽고, 채워져 있으면 아무것도 바꾸지 않는다.
**초안만 교체한다** — 지우는 후속조치는 `status = 'draft'` 인 것뿐이다. 상담원이 손댄(다른 상태의) 항목은 남긴다.
요약·후속조치는 마스킹된 자막에서 나온 것이라 원문이 들어올 자리가 없다(SEC-1).
"""

from __future__ import annotations

from datetime import datetime, timezone

from hub.app.dtos.call_summary_dto import CallSummaryDraft
from hub.app.ports.output.postcall_record_port import PostcallRecordPort, SummaryAlreadyConfirmedError
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

from .connection import ConnectionFactory

DRAFT_STATUS = "draft"  # `follow_up_action.status` — 모델·규칙이 만든 것. 상담원 확정 흐름이 생기면 다른 값을 쓴다

_LOCK_CALL = 'SELECT "summary_confirmed_at" FROM "call" WHERE "call_id" = %s FOR UPDATE'
_UPDATE_CALL = 'UPDATE "call" SET "summary_text" = %s, "inquiry_type" = %s WHERE "call_id" = %s'
_DELETE_DRAFT_ACTIONS = 'DELETE FROM "follow_up_action" WHERE "call_id" = %s AND "status" = %s'
_INSERT_ACTION = (
    'INSERT INTO "follow_up_action" ("call_id", "action_text", "status", "created_at") VALUES (%s, %s, %s, %s)'
)


class PostgresPostcallRepository(PostcallRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def record(self, draft: CallSummaryDraft) -> None:
        now = datetime.now(timezone.utc)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LOCK_CALL, (draft.call_id,))
                row = await cur.fetchone()
                if row is None:
                    raise CallNotStartedError(draft.call_id)
                if row[0] is not None:
                    raise SummaryAlreadyConfirmedError(draft.call_id)

                await cur.execute(_UPDATE_CALL, (draft.summary_text, draft.inquiry_type, draft.call_id))
                await cur.execute(_DELETE_DRAFT_ACTIONS, (draft.call_id, DRAFT_STATUS))
                if draft.follow_up_actions:
                    await cur.executemany(
                        _INSERT_ACTION,
                        [(draft.call_id, a.action_text[:200], DRAFT_STATUS, now) for a in draft.follow_up_actions],
                    )
            await conn.commit()
