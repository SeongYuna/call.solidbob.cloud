# Requirement: B-5, E-1
"""RecommendationRecordPort 의 PostgreSQL 구현 — `recommendation` 1행 + `recommendation_card` 여러 행을 한 트랜잭션에.

**근거 조항은 `document` 에 있을 때만 잇는다.** `recommendation_card.source_doc_id` 가 `document` 를 외래키로 잡는데,
조항 본문은 ES 에만 적재되고 `document` 는 비어 있을 수 있다(2026-09-14 미결 — 운영 `seed_documents.py` 미실행이면
그대로 23503). 콜 가드 저장과 같은 방식으로, 없는 조항이면 NULL 로 두고 카드 제목·요약은 남긴다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hub.app.dtos.recommendation_card_dto import RecommendationCards
from hub.app.ports.output.recommendation_record_port import RecommendationRecordPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

from .connection import ConnectionFactory

_FOREIGN_KEY_VIOLATION = "23503"
TITLE_MAX_CHARS = 100  # `recommendation_card.title` VARCHAR(100)

_INSERT_RECOMMENDATION = """
INSERT INTO "recommendation" ("call_id", "trigger_at_ms", "internal_latency_ms", "e2e_latency_ms", "created_at")
VALUES (%s, %s, %s, %s, %s)
RETURNING "recommendation_id"
"""
_INSERT_CARD = """
INSERT INTO "recommendation_card" ("recommendation_id", "source_doc_id", "title", "summary", "similarity_score", "rank")
VALUES (%s, (SELECT "document_id" FROM "document" WHERE "document_id" = %s), %s, %s, %s, %s)
RETURNING "card_id"
"""


class PostgresRecommendationRepository(RecommendationRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def record(self, cards: RecommendationCards) -> tuple[int | None, ...]:
        card_ids: list[int | None] = []
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(_INSERT_RECOMMENDATION, (
                        cards.call_id, cards.trigger_at_ms, cards.internal_latency_ms, cards.e2e_latency_ms,
                        datetime.now(timezone.utc),
                    ))
                except Exception as exc:
                    # 이 INSERT 가 참조하는 외래키는 call 하나뿐이다 — 통화 시작(POST /hub/calls)이 안 왔다
                    if getattr(exc, "sqlstate", None) == _FOREIGN_KEY_VIOLATION:
                        raise CallNotStartedError(cards.call_id) from exc
                    raise
                recommendation_id = (await cur.fetchone())[0]
                for rank, card in enumerate(cards.cards, 1):  # 배열 순서 = rank (7.3절 v2)
                    await cur.execute(_INSERT_CARD, (
                        recommendation_id, card.source.doc_id, card.title[:TITLE_MAX_CHARS], card.summary,
                        card.similarity_score, rank,
                    ))
                    card_ids.append((await cur.fetchone())[0])
            await conn.commit()
        return tuple(card_ids)
