# Requirement: F-2, QUA-1
"""필요서류 판정 기록 — 헤더 한 행 + 서류별 항목(규칙표 순서)."""

import asyncio

import pytest

from hub.adapter.outbound.postgres.closure_repository import PostgresClosureRepository
from hub.app.dtos import ClosureVerdict, Source


@pytest.mark.integration
def test_실제_DB에_헤더와_항목이_순서대로_남는다(integration_settings):
    from hub.adapter.outbound.postgres.connection import build_connection_factory

    connect = build_connection_factory(integration_settings)
    call_id = "it_f2_001"

    async def scenario():
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute('DELETE FROM "closure_item" WHERE "closure_id" IN (SELECT "closure_id" FROM "closure" WHERE "call_id" = %s)', (call_id,))
                await cur.execute('DELETE FROM "closure" WHERE "call_id" = %s', (call_id,))
                await cur.execute('DELETE FROM "call" WHERE "call_id" = %s', (call_id,))
                await cur.execute('INSERT INTO "call" (call_id, domain, started_at, channel_count, stt_engine, status)'
                                  " VALUES (%s,'dasan',NOW(),1,'google-stt','closed')", (call_id,))
            await conn.commit()
        await PostgresClosureRepository(connect).record(ClosureVerdict(
            call_id=call_id, procedure="DASAN-TERM-4.4", evidence={"신고서": True, "신고인 신분증": False},
            verdict="incomplete", missing=("신고인 신분증",), detected=True,
            source=Source(doc_id="DASAN-TERM-4.4", title="전입신고 — 필요서류"),
        ))
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT "procedure", "verdict", "detected", "source_doc_id", "closure_id" FROM "closure" WHERE "call_id" = %s', (call_id,))
                head = await cur.fetchone()
                await cur.execute('SELECT "rank", "document_name", "informed" FROM "closure_item" WHERE "closure_id" = %s ORDER BY "rank"', (head[4],))
                return head[:4], await cur.fetchall()

    head, items = asyncio.run(scenario())
    assert head == ("DASAN-TERM-4.4", "incomplete", True, "DASAN-TERM-4.4")
    assert items == [(1, "신고서", True), (2, "신고인 신분증", False)]
