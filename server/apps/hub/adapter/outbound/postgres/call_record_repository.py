# Requirement: B-5, D-1, D-3, F-2, SEC-1
"""CallRecordPort 의 PostgreSQL 구현 — `call` · `follow_up_action` · `recommendation`+`recommendation_card` · `closure`+`closure_item`.

읽기만 한다. 담긴 글자는 전부 마스킹된 자막에서 나온 것이다(요약·카드·판정) — 원문 컬럼이 없다(SEC-1).
"""

from __future__ import annotations

from collections import defaultdict

from hub.app.dtos.call_record_dto import (
    CallRecord,
    SavedCard,
    SavedClosure,
    SavedClosureItem,
    SavedFollowUp,
    SavedRecommendation,
)
from hub.app.ports.output.call_record_port import CallRecordPort

from .connection import ConnectionFactory

_CALL = """
SELECT "call_id", "status", "started_at", "ended_at", "summary_text", "inquiry_type", "summary_confirmed_at", "customer_id"
FROM "call" WHERE "call_id" = %s
"""
_FOLLOW_UPS = 'SELECT "action_text", "status" FROM "follow_up_action" WHERE "call_id" = %s ORDER BY "created_at", "id"'
_RECOMMENDATIONS = """
SELECT "recommendation_id", "trigger_at_ms", "internal_latency_ms", "created_at"
FROM "recommendation" WHERE "call_id" = %s ORDER BY "created_at", "recommendation_id"
"""
_CARDS = """
SELECT c."recommendation_id", c."card_id", c."rank", c."title", c."summary", c."source_doc_id", c."similarity_score"
FROM "recommendation_card" c JOIN "recommendation" r ON r."recommendation_id" = c."recommendation_id"
WHERE r."call_id" = %s ORDER BY c."recommendation_id", c."rank"
"""
_CLOSURES = """
SELECT "closure_id", "procedure", "verdict", "detected", "reason", "source_doc_id", "decided_at"
FROM "closure" WHERE "call_id" = %s ORDER BY "decided_at", "closure_id"
"""
_CLOSURE_ITEMS = """
SELECT i."closure_id", i."rank", i."document_name", i."informed"
FROM "closure_item" i JOIN "closure" c ON c."closure_id" = i."closure_id"
WHERE c."call_id" = %s ORDER BY i."closure_id", i."rank"
"""


class PostgresCallRecordRepository(CallRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def get(self, call_id: str) -> CallRecord | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_CALL, (call_id,))
                call = await cur.fetchone()
                if call is None:
                    return None
                await cur.execute(_FOLLOW_UPS, (call_id,))
                follow_ups = await cur.fetchall()
                await cur.execute(_RECOMMENDATIONS, (call_id,))
                recommendations = await cur.fetchall()
                await cur.execute(_CARDS, (call_id,))
                cards = await cur.fetchall()
                await cur.execute(_CLOSURES, (call_id,))
                closures = await cur.fetchall()
                await cur.execute(_CLOSURE_ITEMS, (call_id,))
                items = await cur.fetchall()

        cards_by_rec: dict[int, list[SavedCard]] = defaultdict(list)
        for rec_id, card_id, rank, title, summary, source_doc_id, score in cards:
            cards_by_rec[rec_id].append(SavedCard(card_id=card_id, rank=rank, title=title, summary=summary,
                                                  source_doc_id=source_doc_id,
                                                  similarity_score=None if score is None else float(score)))
        items_by_closure: dict[int, list[SavedClosureItem]] = defaultdict(list)
        for closure_id, rank, name, informed in items:
            items_by_closure[closure_id].append(SavedClosureItem(rank=rank, document_name=name, informed=informed))

        cid, status, started_at, ended_at, summary_text, inquiry_type, confirmed_at, customer_id = call
        return CallRecord(
            call_id=cid, status=status, started_at=started_at, ended_at=ended_at, customer_id=customer_id,
            summary_text=summary_text, inquiry_type=inquiry_type, summary_confirmed_at=confirmed_at,
            follow_up_actions=tuple(SavedFollowUp(action_text=t, status=s) for t, s in follow_ups),
            recommendations=tuple(
                SavedRecommendation(recommendation_id=rid, trigger_at_ms=trig, internal_latency_ms=lat, created_at=at,
                                    cards=tuple(cards_by_rec.get(rid, ())))
                for rid, trig, lat, at in recommendations
            ),
            closures=tuple(
                SavedClosure(closure_id=clid, procedure=proc, verdict=verdict, detected=detected, reason=reason,
                             source_doc_id=src, decided_at=at, items=tuple(items_by_closure.get(clid, ())))
                for clid, proc, verdict, detected, reason, src, at in closures
            ),
        )
