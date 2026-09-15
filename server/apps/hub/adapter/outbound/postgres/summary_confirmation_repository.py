# Requirement: D-1, D-2, D-3
"""SummaryConfirmationPort 의 PostgreSQL 구현 — 한 트랜잭션에 `call` 확정 + 후속조치 초안 교체.

`summary_confirmed_at` 을 행 잠금으로 읽어 이미 확정됐으면 아무것도 바꾸지 않는다(`postcall_repository.py` 와 같은 잠금).
지우는 후속조치는 `draft` 뿐이다 — 초안 저장이 넣은 것만 교체하고, 다른 상태의 항목은 남긴다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hub.app.ports.output.postcall_record_port import SummaryAlreadyConfirmedError
from hub.app.ports.output.summary_confirmation_port import SummaryConfirmationPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

from .connection import ConnectionFactory
from .postcall_repository import DRAFT_STATUS

CONFIRMED_STATUS = "confirmed"  # `follow_up_action.status` — 상담원이 확정한 후속조치

_LOCK_CALL = 'SELECT "summary_confirmed_at" FROM "call" WHERE "call_id" = %s FOR UPDATE'
_CONFIRM_CALL = """
UPDATE "call" SET "summary_text" = %s, "inquiry_type" = %s, "summary_confirmed_at" = %s WHERE "call_id" = %s
"""
_DELETE_DRAFT_ACTIONS = 'DELETE FROM "follow_up_action" WHERE "call_id" = %s AND "status" = %s'
_INSERT_ACTION = (
    'INSERT INTO "follow_up_action" ("call_id", "action_text", "status", "created_at") VALUES (%s, %s, %s, %s)'
)


class PostgresSummaryConfirmationRepository(SummaryConfirmationPort):
    def __init__(self, connect: ConnectionFactory, now=lambda: datetime.now(timezone.utc)) -> None:
        self._connect = connect
        self._now = now

    async def confirm(
        self, call_id: str, *, summary_text: str, inquiry_type: str | None, follow_up_actions: tuple[str, ...]
    ) -> datetime:
        now = self._now()
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LOCK_CALL, (call_id,))
                row = await cur.fetchone()
                if row is None:
                    raise CallNotStartedError(call_id)
                if row[0] is not None:
                    raise SummaryAlreadyConfirmedError(call_id)
                await cur.execute(_CONFIRM_CALL, (summary_text, inquiry_type, now, call_id))
                await cur.execute(_DELETE_DRAFT_ACTIONS, (call_id, DRAFT_STATUS))
                if follow_up_actions:
                    await cur.executemany(_INSERT_ACTION, [(call_id, a, CONFIRMED_STATUS, now) for a in follow_up_actions])
            await conn.commit()
        return now
