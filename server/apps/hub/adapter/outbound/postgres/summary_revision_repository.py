# Requirement: D-1, D-2, D-3
"""SummaryRevisionPort 의 PostgreSQL 구현 — 한 트랜잭션에 이력 1행 + `call` 갱신 + 후속조치 대체.

**지우지 않는다.** 이전 요약·유형은 `call_summary_revision` 에, 이전 확정 후속조치는 `status = 'superseded'` 로 남는다 —
틀린 확정을 고친 기록이 사라지면 «처음부터 맞았던 것» 처럼 보인다(절대 원칙 8 과 같은 방향).
`summary_confirmed_at` 은 처음 확정 시각 그대로 둔다 — 고친 시각은 이력의 `revised_at` 이다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hub.app.dtos.summary_revision_dto import SummaryRevision
from hub.app.ports.output.summary_revision_port import SummaryNotConfirmedError, SummaryRevisionPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

from .connection import ConnectionFactory
from .summary_confirmation_repository import CONFIRMED_STATUS

SUPERSEDED_STATUS = "superseded"  # `follow_up_action.status` — 재수정으로 대체된 확정 후속조치

_LOCK_CALL = 'SELECT "summary_text", "inquiry_type", "summary_confirmed_at" FROM "call" WHERE "call_id" = %s FOR UPDATE'
_CALL_EXISTS = 'SELECT 1 FROM "call" WHERE "call_id" = %s'
_REVISION_COLUMNS = '"revision_id", "call_id", "previous_summary_text", "previous_inquiry_type", "reason", "revised_at"'
_INSERT_REVISION = f"""
INSERT INTO "call_summary_revision" ("call_id", "previous_summary_text", "previous_inquiry_type", "reason", "revised_at")
VALUES (%s, %s, %s, %s, %s) RETURNING {_REVISION_COLUMNS}
"""
_UPDATE_CALL = 'UPDATE "call" SET "summary_text" = %s, "inquiry_type" = %s WHERE "call_id" = %s'
_SUPERSEDE_ACTIONS = 'UPDATE "follow_up_action" SET "status" = %s WHERE "call_id" = %s AND "status" = %s'
_INSERT_ACTION = (
    'INSERT INTO "follow_up_action" ("call_id", "action_text", "status", "created_at") VALUES (%s, %s, %s, %s)'
)
_LIST = f'SELECT {_REVISION_COLUMNS} FROM "call_summary_revision" WHERE "call_id" = %s ORDER BY "revised_at", "revision_id"'


def _revision(row) -> SummaryRevision:
    rid, call_id, prev_summary, prev_inquiry, reason, at = row
    return SummaryRevision(revision_id=int(rid), call_id=call_id, previous_summary_text=prev_summary,
                           previous_inquiry_type=prev_inquiry, reason=reason, revised_at=at)


class PostgresSummaryRevisionRepository(SummaryRevisionPort):
    def __init__(self, connect: ConnectionFactory, now=lambda: datetime.now(timezone.utc)) -> None:
        self._connect = connect
        self._now = now

    async def revise(
        self, call_id: str, *, summary_text: str, inquiry_type: str | None, follow_up_actions: tuple[str, ...], reason: str
    ) -> SummaryRevision:
        now = self._now()
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LOCK_CALL, (call_id,))
                row = await cur.fetchone()
                if row is None:
                    raise CallNotStartedError(call_id)
                previous_summary, previous_inquiry, confirmed_at = row
                if confirmed_at is None:
                    raise SummaryNotConfirmedError(call_id)
                await cur.execute(_INSERT_REVISION, (call_id, previous_summary, previous_inquiry, reason, now))
                revision = _revision(await cur.fetchone())
                await cur.execute(_UPDATE_CALL, (summary_text, inquiry_type, call_id))
                await cur.execute(_SUPERSEDE_ACTIONS, (SUPERSEDED_STATUS, call_id, CONFIRMED_STATUS))
                if follow_up_actions:
                    await cur.executemany(_INSERT_ACTION, [(call_id, a, CONFIRMED_STATUS, now) for a in follow_up_actions])
            await conn.commit()
        return revision

    async def list_revisions(self, call_id: str) -> list[SummaryRevision]:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_CALL_EXISTS, (call_id,))
                if await cur.fetchone() is None:
                    raise CallNotStartedError(call_id)
                await cur.execute(_LIST, (call_id,))
                rows = await cur.fetchall()
        return [_revision(r) for r in rows]
