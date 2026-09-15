# Requirement: B-5, E-1, QUA-1
"""추천 저장 — 실제 PostgreSQL(현재 db/schema.sql)에서: card_id 순서 · 없는 조항은 NULL · 없는 통화 · 피드백 외래키.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio

import pytest

from hub.adapter.outbound.postgres.card_feedback_repository import PostgresCardFeedbackRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.recommendation_repository import PostgresRecommendationRepository
from hub.app.dtos.card_feedback_dto import CardFeedback
from hub.app.dtos.recommendation_card_dto import Card, RecommendationCards, Source
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

CALL = "it-recommend-0915"
DOC = "IT-DOC-1"


async def _sql(connect, sql, args=None):
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall() if cur.description else None
        await conn.commit()
    return rows


@pytest.mark.integration
def test_실제_DB에_추천을_저장하고_card_id로_피드백을_받는다(integration_settings):
    connect = build_connection_factory(integration_settings)
    repo = PostgresRecommendationRepository(connect)

    async def cleanup():
        await _sql(connect, 'DELETE FROM "card_feedback" WHERE "card_id" IN (SELECT "card_id" FROM "recommendation_card" '
                            'WHERE "recommendation_id" IN (SELECT "recommendation_id" FROM "recommendation" WHERE "call_id" = %s))', (CALL,))
        await _sql(connect, 'DELETE FROM "recommendation_card" WHERE "recommendation_id" IN '
                            '(SELECT "recommendation_id" FROM "recommendation" WHERE "call_id" = %s)', (CALL,))
        await _sql(connect, 'DELETE FROM "recommendation" WHERE "call_id" = %s', (CALL,))
        await _sql(connect, 'DELETE FROM "call" WHERE "call_id" = %s', (CALL,))
        await _sql(connect, 'DELETE FROM "document" WHERE "document_id" = %s', (DOC,))

    async def scenario():
        await cleanup()
        await _sql(connect, 'INSERT INTO "call" ("call_id","domain","started_at","channel_count","stt_engine","status") '
                            "VALUES (%s, 'dasan', now(), 1, 'mock', 'in_progress')", (CALL,))
        await _sql(connect, 'INSERT INTO "document" ("document_id","doc_type","title","source_path","updated_at") '
                            "VALUES (%s, 'TERM', '통합테스트 조항', 'it/doc.md', now())", (DOC,))
        try:
            cards = RecommendationCards(call_id=CALL, trigger_at_ms=3150, internal_latency_ms=12, cards=(
                Card(title="있는 조항", summary="a", source=Source(doc_id=DOC, title="t"), similarity_score=7.8),
                Card(title="없는 조항", summary="b", source=Source(doc_id="NOT-SEEDED-9.9", title="t"), similarity_score=5.1),
            ))
            ids = await repo.record(cards)
            assert len(ids) == 2 and ids[0] < ids[1]

            rows = await _sql(connect, 'SELECT "card_id","source_doc_id","title","rank" FROM "recommendation_card" '
                                       'WHERE "card_id" = ANY(%s) ORDER BY "rank"', (list(ids),))
            assert rows == [(ids[0], DOC, "있는 조항", 1), (ids[1], None, "없는 조항", 2)]  # 없는 조항은 NULL, 저장은 된다

            feedback_id = await PostgresCardFeedbackRepository(connect).append(CardFeedback(card_id=ids[1], action="adopted"))
            assert feedback_id is not None  # 돌려준 card_id 로 피드백 외래키가 성립한다

            assert await repo.record(RecommendationCards(call_id=CALL, trigger_at_ms=1)) == ()  # 관련 문서 없음도 저장

            with pytest.raises(CallNotStartedError):
                await repo.record(RecommendationCards(call_id="it-no-such-call", trigger_at_ms=1))
        finally:
            await cleanup()

    asyncio.run(scenario())
