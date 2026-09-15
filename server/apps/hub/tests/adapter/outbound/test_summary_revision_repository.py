# Requirement: D-1, D-2, D-3, QUA-1
"""요약 재수정 — 실제 PostgreSQL(현재 db/schema.sql): 확정 전 거부 · 이전 값 이력 · 후속조치 superseded · 두 번 고치면 이력 2건.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio

import pytest

from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.summary_confirmation_repository import PostgresSummaryConfirmationRepository
from hub.adapter.outbound.postgres.summary_revision_repository import SUPERSEDED_STATUS, PostgresSummaryRevisionRepository
from hub.app.ports.output.summary_revision_port import SummaryNotConfirmedError
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

CALL = "it-summary-revision-0915"


async def _sql(connect, sql, args=None, fetch=False):
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall() if fetch else None
        await conn.commit()
    return rows


@pytest.mark.integration
def test_실제_DB에서_확정본을_고치고_이전_값을_남긴다(integration_settings):
    connect = build_connection_factory(integration_settings)

    async def cleanup():
        for q in ['DELETE FROM "call_summary_revision" WHERE "call_id" = %s',
                  'DELETE FROM "follow_up_action" WHERE "call_id" = %s', 'DELETE FROM "call" WHERE "call_id" = %s']:
            await _sql(connect, q, (CALL,))

    async def scenario():
        await cleanup()
        await _sql(connect, 'INSERT INTO "call" ("call_id","domain","started_at","channel_count","stt_engine","status") '
                            "VALUES (%s, 'dasan', now(), 1, 'mock', 'in_progress')", (CALL,))
        repo = PostgresSummaryRevisionRepository(connect)
        try:
            with pytest.raises(SummaryNotConfirmedError):  # 확정 전에는 고치지 않는다
                await repo.revise(CALL, summary_text="x", inquiry_type=None, follow_up_actions=(), reason="x")

            confirmed_at = await PostgresSummaryConfirmationRepository(connect).confirm(
                CALL, summary_text="처음 확정", inquiry_type="기타", follow_up_actions=("확정 조치",))
            first = await repo.revise(CALL, summary_text="고친 요약", inquiry_type="전입신고",
                                      follow_up_actions=("새 조치",), reason="유형 오기")
            assert (first.previous_summary_text, first.previous_inquiry_type, first.reason) == ("처음 확정", "기타", "유형 오기")

            call = await _sql(connect, 'SELECT "summary_text","inquiry_type","summary_confirmed_at" FROM "call" WHERE "call_id"=%s', (CALL,), fetch=True)
            assert call == [("고친 요약", "전입신고", confirmed_at)]  # 확정 시각은 처음 그대로
            actions = await _sql(connect, 'SELECT "action_text","status" FROM "follow_up_action" WHERE "call_id"=%s ORDER BY "id"', (CALL,), fetch=True)
            assert actions == [("확정 조치", SUPERSEDED_STATUS), ("새 조치", "confirmed")]  # 지우지 않고 대체 표시

            second = await repo.revise(CALL, summary_text="또 고친 요약", inquiry_type=None, follow_up_actions=(), reason="문구")
            assert second.previous_summary_text == "고친 요약"
            assert [r.revision_id for r in await repo.list_revisions(CALL)] == [first.revision_id, second.revision_id]

            with pytest.raises(CallNotStartedError):
                await repo.list_revisions("it-no-such-call")
        finally:
            await cleanup()

    asyncio.run(scenario())
