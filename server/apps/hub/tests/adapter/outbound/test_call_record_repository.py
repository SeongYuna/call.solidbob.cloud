# Requirement: B-5, D-1, F-2, QUA-1
"""통화 기록 조회 — 실제 PostgreSQL(현재 db/schema.sql)에서 기존 저장 어댑터들이 남긴 것을 한 번에 읽는다.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio

import pytest

from hub.adapter.outbound.postgres.call_record_repository import PostgresCallRecordRepository
from hub.adapter.outbound.postgres.closure_repository import PostgresClosureRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.postcall_repository import PostgresPostcallRepository
from hub.adapter.outbound.postgres.recommendation_repository import PostgresRecommendationRepository
from hub.app.dtos.call_summary_dto import CallSummaryDraft, FollowUpAction
from hub.app.dtos.closure_verdict_dto import ClosureVerdict
from hub.app.dtos.recommendation_card_dto import Card, RecommendationCards, Source

CALL = "it-call-record-0915"


async def _sql(connect, sql, args=None):
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
        await conn.commit()


@pytest.mark.integration
def test_실제_DB에서_저장_어댑터들이_남긴_기록을_한_번에_읽는다(integration_settings):
    connect = build_connection_factory(integration_settings)

    async def cleanup():
        for q in ['DELETE FROM "closure_item" WHERE "closure_id" IN (SELECT "closure_id" FROM "closure" WHERE "call_id" = %s)',
                  'DELETE FROM "closure" WHERE "call_id" = %s',
                  'DELETE FROM "recommendation_card" WHERE "recommendation_id" IN (SELECT "recommendation_id" FROM "recommendation" WHERE "call_id" = %s)',
                  'DELETE FROM "recommendation" WHERE "call_id" = %s',
                  'DELETE FROM "follow_up_action" WHERE "call_id" = %s',
                  'DELETE FROM "call" WHERE "call_id" = %s']:
            await _sql(connect, q, (CALL,))

    async def scenario():
        await cleanup()
        await _sql(connect, 'INSERT INTO "call" ("call_id","domain","started_at","channel_count","stt_engine","status") '
                            "VALUES (%s, 'dasan', now(), 1, 'mock', 'in_progress')", (CALL,))
        try:
            repo = PostgresCallRecordRepository(connect)
            empty = await repo.get(CALL)
            assert empty.summary_text is None and empty.recommendations == () and empty.closures == ()
            assert empty.customer_id is None  # 발신 번호 없이 연 통화 — 컬럼을 실제로 읽는지(w6-call-record-customer-id)

            ids = await PostgresRecommendationRepository(connect).record(RecommendationCards(
                call_id=CALL, trigger_at_ms=3150, internal_latency_ms=9, cards=(
                    Card(title="첫째", summary="a", source=Source(doc_id="NOT-SEEDED", title="t"), similarity_score=7.5),
                    Card(title="둘째", summary="b", source=Source(doc_id="NOT-SEEDED-2", title="t"), similarity_score=6.0))))
            await PostgresRecommendationRepository(connect).record(RecommendationCards(call_id=CALL, trigger_at_ms=5000))
            await PostgresClosureRepository(connect).record(ClosureVerdict(
                call_id=CALL, procedure="DASAN-TERM-4.3", procedure_title="초본", evidence={"신분증": True, "위임장": False},
                verdict="incomplete", missing=("위임장",), detected=True))
            await PostgresPostcallRepository(connect).record(CallSummaryDraft(
                call_id=CALL, summary_text="요약 초안", follow_up_actions=(FollowUpAction(action_text="회신 드리겠습니다"),)))

            r = await repo.get(CALL)
            assert r.summary_text == "요약 초안" and r.summary_confirmed_at is None
            assert [(f.action_text, f.status) for f in r.follow_up_actions] == [("회신 드리겠습니다", "draft")]
            first, second = r.recommendations
            assert [(c.card_id, c.rank, c.title, c.source_doc_id) for c in first.cards] == [
                (ids[0], 1, "첫째", None), (ids[1], 2, "둘째", None)]
            assert first.cards[0].similarity_score == pytest.approx(7.5)
            assert second.trigger_at_ms == 5000 and second.cards == ()
            (closure,) = r.closures
            assert closure.verdict == "incomplete" and closure.detected is True
            assert [(i.rank, i.document_name, i.informed) for i in closure.items] == [(1, "신분증", True), (2, "위임장", False)]

            assert await repo.get("it-no-such-call") is None
        finally:
            await cleanup()

    asyncio.run(scenario())
