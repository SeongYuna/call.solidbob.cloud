# Requirement: D-4, QUA-1
"""공백 리포트 조회 리포지토리 — **SQL 이 도는지는 실제 DB 로만 알 수 있다.**

가짜 커넥션으로는 "쿼리를 보냈다"까지만 확인된다. 필터 조합·`FILTER (WHERE ...)` 집계·
LEFT JOIN 은 문법이 틀려도 가짜 커서에서는 통과하므로, 여기서는 실제 PostgreSQL 로 본다.

    cd infra && docker compose up -d
    cd ../server && ../.venv/bin/python -m pytest -m integration
"""

import asyncio

import pytest

from hub.adapter.outbound.postgres.knowledge_gap_query_repository import (
    PostgresKnowledgeGapQueryRepository,
)
from hub.app.dtos.knowledge_gap_query_dto import KnowledgeGapQuery

CALL_ID = "it_gap_001"


@pytest.mark.integration
def test_실제_DB에서_조회_집계_상태전이가_돈다(integration_settings):
    from hub.adapter.outbound.postgres.connection import build_connection_factory

    connect = build_connection_factory(integration_settings)
    repo = PostgresKnowledgeGapQueryRepository(connect)

    async def scenario():
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute('DELETE FROM "knowledge_gap" WHERE "call_id"=%s OR "description" LIKE %s',
                                  (CALL_ID, "it_gap%"))
                await cur.execute('DELETE FROM "call" WHERE call_id=%s', (CALL_ID,))
                await cur.execute(
                    'INSERT INTO "call" (call_id, domain, started_at, channel_count, stt_engine, status)'
                    " VALUES (%s,'shopping',NOW(),1,'google-stt','closed')", (CALL_ID,))
                # 통화가 연결된 신고 2건 + 통화가 없는 신고 1건
                await cur.execute(
                    'INSERT INTO "knowledge_gap" ("module","description","call_id","created_at","status")'
                    " VALUES ('B','it_gap 검색 실패',%s,NOW(),'open') RETURNING id", (CALL_ID,))
                gap_open = (await cur.fetchone())[0]
                await cur.execute(
                    'INSERT INTO "knowledge_gap" ("module","description","call_id","created_at","status")'
                    " VALUES ('C','it_gap 놓친 위반',%s,NOW(),'resolved')", (CALL_ID,))
                await cur.execute(
                    'INSERT INTO "knowledge_gap" ("module","description","created_at","status")'
                    " VALUES ('F','it_gap 통화 없는 신고',NOW(),'open')")
            await conn.commit()

        mine = KnowledgeGapQuery(limit=200)
        rows = [r for r in await repo.list_gaps(mine) if r.description.startswith("it_gap")]
        assert len(rows) == 3

        # LEFT JOIN — 통화가 없는 신고가 사라지지 않고 domain 만 None 이다
        없는통화 = [r for r in rows if r.call_id is None]
        assert len(없는통화) == 1 and 없는통화[0].domain is None
        assert {r.domain for r in rows if r.call_id} == {"shopping"}

        # 필터
        only_b = await repo.list_gaps(KnowledgeGapQuery(module="B", limit=200))
        assert all(r.module == "B" for r in only_b)
        only_open = await repo.list_gaps(KnowledgeGapQuery(status="open", limit=200))
        assert all(r.status == "open" for r in only_open)
        assert await repo.count_gaps(KnowledgeGapQuery(module="B")) == len(
            await repo.list_gaps(KnowledgeGapQuery(module="B", limit=200)))

        # 집계 — FILTER (WHERE ...) 문법이 실제로 도는지
        by_module = {c.key: c for c in await repo.count_by_module()}
        assert by_module["B"].open >= 1 and by_module["C"].resolved >= 1
        by_domain = {c.key: c for c in await repo.count_by_domain()}
        assert "shopping" in by_domain

        # 상태 전이
        assert await repo.update_status(gap_open, "resolved") is True
        after = [r for r in await repo.list_gaps(KnowledgeGapQuery(limit=200)) if r.gap_id == gap_open]
        assert after[0].status == "resolved"
        # 없는 id 는 옮겼다고 하지 않는다
        assert await repo.update_status(-1, "resolved") is False

        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute('DELETE FROM "knowledge_gap" WHERE "description" LIKE %s', ("it_gap%",))
                await cur.execute('DELETE FROM "call" WHERE call_id=%s', (CALL_ID,))
            await conn.commit()

    asyncio.run(scenario())
