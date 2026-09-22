# Requirement: J-3, J-5, QUA-1
"""실제 PostgreSQL(현재 db/schema.sql)에서 현황판 건수 — 넣은 만큼 늘고, 해제·만료된 등록과 결정된 요청은 세지 않는다.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio

import pytest

from hub.adapter.outbound.postgres.admin_stats_repository import PostgresAdminStatsRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory

REF = "e" * 64
CALLS = ("it_stats_a", "it_stats_b")


@pytest.mark.integration
def test_실제_DB에서_현황판_건수(integration_settings):
    connect = build_connection_factory(integration_settings)
    repo = PostgresAdminStatsRepository(connect)

    async def sql(q, args=None):
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(q, args)
                rows = await cur.fetchall() if cur.description else None
            await conn.commit()
        return rows

    async def reset():
        await sql('DELETE FROM "routing_log" WHERE "call_id" = ANY(%s)', (list(CALLS),))
        await sql('DELETE FROM "blacklist_entry" WHERE "customer_ref" = %s', (REF,))
        await sql('DELETE FROM "blacklist_request" WHERE "customer_ref" = %s', (REF,))
        await sql('DELETE FROM "call_guard_flag" WHERE "call_id" = ANY(%s)', (list(CALLS),))
        await sql('DELETE FROM "transcript_segment" WHERE "call_id" = ANY(%s)', (list(CALLS),))
        await sql('DELETE FROM "call" WHERE "call_id" = ANY(%s)', (list(CALLS),))

    async def scenario():
        await reset()
        before = await repo.count()
        try:
            await sql("""INSERT INTO "agent" ("agent_id","display_name","role") VALUES ('it-stats-agent','상담원','agent')
                         ON CONFLICT DO NOTHING""")
            await sql('INSERT INTO "customer" VALUES (%s, NOW(), %s) ON CONFLICT DO NOTHING', (REF, "active"))
            await sql("""INSERT INTO "call" (call_id, domain, customer_id, started_at, channel_count, stt_engine, status)
                         VALUES ('it_stats_a','dasan',%s,NOW(),1,'mock','closed'),
                                ('it_stats_b','dasan',%s,NOW(),1,'mock','in_progress')""", (REF, REF))
            await sql("""INSERT INTO "transcript_segment" (segment_id, call_id, speaker, text, is_final, created_at)
                         VALUES (1,'it_stats_a','customer','*** 같은',TRUE,NOW())""")
            await sql("""INSERT INTO "call_guard_flag" (call_id, segment_id, category, phrase, span_start, span_end, detected_at)
                         VALUES ('it_stats_a',1,'insult','***',0,3,NOW())""")
            ids = {}
            for key, call_id, status in (("pending", "it_stats_a", "pending"), ("rejected", "it_stats_b", "rejected"),
                                         ("live", "it_stats_a", "approved"), ("old", "it_stats_b", "approved")):
                (ids[key],), = await sql("""INSERT INTO "blacklist_request" (call_id, customer_ref, requested_by, reason, context_excerpt,
                             call_duration_s, insult_count, threat_count, sexual_count, status, requested_at, evidence_snapshot_at)
                             VALUES (%s,%s,'it-stats-agent','사유','자막',1,1,0,0,%s,NOW(),NOW())
                             RETURNING request_id""",
                                         (call_id, REF, status))
            # 적용 중 1 · 이미 만료돼 닫힘 1 (닫힌 것은 세지 않는다)
            await sql("""INSERT INTO "blacklist_entry" ("customer_ref","request_id","approved_at","expires_at")
                         VALUES (%s, %s, NOW(), NOW() + INTERVAL '30 days')""", (REF, ids["live"]))
            await sql("""INSERT INTO "blacklist_entry" ("customer_ref","request_id","approved_at","expires_at","released_at","release_reason")
                         VALUES (%s, %s, NOW() - INTERVAL '60 days', NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days', '만료')""",
                      (REF, ids["old"]))
            await sql("""INSERT INTO "routing_log" (call_id, is_blacklisted, fell_back, reason, routed_at)
                         VALUES ('it_stats_a', TRUE, TRUE, '베테랑 없음', NOW()), ('it_stats_b', FALSE, FALSE, '일반', NOW())""")

            after = await repo.count()
            diff = {k: getattr(after, k) - getattr(before, k) for k in (
                "calls_total", "calls_closed", "call_guard_flags", "pending_requests", "active_entries",
                "routing_decisions", "routing_blacklisted", "routing_fell_back")}
            assert diff == {"calls_total": 2, "calls_closed": 1, "call_guard_flags": 1, "pending_requests": 1,
                            "active_entries": 1, "routing_decisions": 2, "routing_blacklisted": 1, "routing_fell_back": 1}
            assert after.counted_at is not None
        finally:
            await reset()

    asyncio.run(scenario())
