# Requirement: D-1, D-2, D-3, QUA-1
"""요약 확정 — 실제 PostgreSQL(현재 db/schema.sql)에서: 초안 → 확정 · 초안 후속조치 교체 · 두 번째 확정·재초안 거부.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio

import pytest

from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.postcall_repository import PostgresPostcallRepository
from hub.adapter.outbound.postgres.summary_confirmation_repository import (
    CONFIRMED_STATUS,
    PostgresSummaryConfirmationRepository,
)
from hub.app.dtos.call_summary_dto import CallSummaryDraft, FollowUpAction
from hub.app.ports.output.postcall_record_port import SummaryAlreadyConfirmedError
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

CALL = "it-summary-confirm-0915"


async def _sql(connect, sql, args=None, fetch=False):
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall() if fetch else None
        await conn.commit()
    return rows


@pytest.mark.integration
def test_실제_DB에서_초안을_고쳐_확정하고_다시는_덮지_않는다(integration_settings):
    connect = build_connection_factory(integration_settings)

    async def cleanup():
        await _sql(connect, 'DELETE FROM "follow_up_action" WHERE "call_id" = %s', (CALL,))
        await _sql(connect, 'DELETE FROM "call" WHERE "call_id" = %s', (CALL,))

    async def scenario():
        await cleanup()
        await _sql(connect, 'INSERT INTO "call" ("call_id","domain","started_at","channel_count","stt_engine","status") '
                            "VALUES (%s, 'dasan', now(), 1, 'mock', 'in_progress')", (CALL,))
        try:
            await PostgresPostcallRepository(connect).record(CallSummaryDraft(
                call_id=CALL, summary_text="규칙 초안", follow_up_actions=(FollowUpAction(action_text="초안 조치"),)))
            repo = PostgresSummaryConfirmationRepository(connect)
            at = await repo.confirm(CALL, summary_text="상담원이 고친 요약", inquiry_type="전입신고",
                                    follow_up_actions=("확정 조치 A", "확정 조치 B"))

            call = await _sql(connect, 'SELECT "summary_text","inquiry_type","summary_confirmed_at" FROM "call" WHERE "call_id"=%s', (CALL,), fetch=True)
            assert call == [("상담원이 고친 요약", "전입신고", at)]
            actions = await _sql(connect, 'SELECT "action_text","status" FROM "follow_up_action" WHERE "call_id"=%s ORDER BY "id"', (CALL,), fetch=True)
            assert actions == [("확정 조치 A", CONFIRMED_STATUS), ("확정 조치 B", CONFIRMED_STATUS)]  # 초안은 교체됐다

            with pytest.raises(SummaryAlreadyConfirmedError):  # 확정은 한 번
                await repo.confirm(CALL, summary_text="또", inquiry_type=None, follow_up_actions=())
            with pytest.raises(SummaryAlreadyConfirmedError):  # 확정 뒤 초안 재생성도 덮지 않는다
                await PostgresPostcallRepository(connect).record(CallSummaryDraft(call_id=CALL, summary_text="새 초안"))
            with pytest.raises(CallNotStartedError):
                await repo.confirm("it-no-such-call", summary_text="x", inquiry_type=None, follow_up_actions=())
        finally:
            await cleanup()

    asyncio.run(scenario())
