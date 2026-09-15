# Requirement: J-5, QUA-1
"""J-5 배정 판정 — 실제 PostgreSQL: 블랙리스트 고객은 베테랑 · 기준 설정이 판정에 반영 · 베테랑 없으면 떨어뜨림 · routing_log 기록.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest

from blacklist.adapter.outbound.postgres_agent_routing_adapter import PostgresAgentRoutingAdapter
from blacklist.adapter.outbound.postgres_routing_setting_repository import PostgresRoutingSettingRepository
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

REF = "9" * 64
CALLS = {"it_route_bl": REF, "it_route_plain": None, "it_route_anon": None}
AGENTS = {"it-vet": 6, "it-mid": 4, "it-new": 1}  # 근속 연수


@pytest.mark.integration
def test_실제_DB_배정_판정(integration_settings):
    from hub.adapter.outbound.postgres.connection import build_connection_factory

    connect = build_connection_factory(integration_settings)
    now = datetime.now(timezone.utc)

    async def sql(q, args=None, fetch=False):
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(q, args)
                rows = await cur.fetchall() if fetch else None
            await conn.commit()
        return rows

    async def reset():
        for call_id in CALLS:
            await sql('DELETE FROM "routing_log" WHERE "call_id" = %s', (call_id,))
        await sql('DELETE FROM "blacklist_entry" WHERE "customer_ref" = %s', (REF,))
        await sql('DELETE FROM "blacklist_request" WHERE "customer_ref" = %s', (REF,))
        for call_id in CALLS:
            await sql('DELETE FROM "call" WHERE "call_id" = %s', (call_id,))
        await sql('DELETE FROM "app_setting" WHERE "setting_key" = %s', ("veteran_years",))

    async def scenario():
        await reset()
        for agent_id, years in AGENTS.items():
            hired = date.today() - timedelta(days=int(years * 365.25) + 2)
            await sql('INSERT INTO "agent" ("agent_id","display_name","role","hired_on") VALUES (%s,%s,%s,%s) '
                      'ON CONFLICT ("agent_id") DO UPDATE SET "hired_on" = EXCLUDED."hired_on"', (agent_id, agent_id, "agent", hired))
        await sql('INSERT INTO "customer" VALUES (%s, NOW(), %s) ON CONFLICT DO NOTHING', (REF, "active"))
        for call_id, ref in CALLS.items():
            await sql("INSERT INTO \"call\" (call_id, domain, customer_id, started_at, channel_count, stt_engine, status) "
                      "VALUES (%s,'dasan',%s,NOW(),1,'mock','in_progress')", (call_id, ref))
        # 적용 중 블랙리스트 등록(요청 → 등록을 직접 넣는다 — 승인 흐름은 다른 테스트가 본다)
        await sql("""INSERT INTO "blacklist_request" (call_id, customer_ref, requested_by, reason, context_excerpt, call_duration_s,
                     insult_count, threat_count, sexual_count, temperature_outliers, status, requested_at, evidence_snapshot_at)
                     VALUES ('it_route_bl', %s, 'it-new', '폭언', '…', 1, 1, 0, 0, 0, 'approved', NOW(), NOW())""", (REF,))
        (rid,), = await sql('SELECT "request_id" FROM "blacklist_request" WHERE "customer_ref" = %s', (REF,), fetch=True)
        await sql('INSERT INTO "blacklist_entry" (customer_ref, request_id, approved_at, expires_at) VALUES (%s, %s, NOW(), %s)',
                  (REF, rid, now + timedelta(days=30)))
        routing = PostgresAgentRoutingAdapter(connect)
        settings = PostgresRoutingSettingRepository(connect)
        try:
            assert (await settings.get()).saved is False  # 저장값 없음 → 기본 3년

            bl = await routing.route_call("it_route_bl", ("it-new", "it-mid", "it-vet", "ghost"))
            assert (bl.decision.is_blacklisted, bl.decision.agent_id, bl.decision.fell_back) == (True, "it-vet", False)
            assert bl.veteran_years == 3.0 and bl.unknown_candidates == ("ghost",) and bl.customer_identified is True

            # 기준을 5년으로 → 6년차만 베테랑. 6년차가 후보에 없으면 떨어뜨린다
            saved = await settings.save(5.0, None)
            assert saved.saved is True and saved.veteran_years == 5.0
            fb = await routing.route_call("it_route_bl", ("it-new", "it-mid"))
            assert (fb.decision.agent_id, fb.decision.fell_back, fb.veteran_years) == ("it-mid", True, 5.0)

            plain = await routing.route_call("it_route_plain", ("it-vet",))
            assert (plain.decision.is_blacklisted, plain.decision.agent_id, plain.customer_identified) == (False, None, False)

            logs = await sql('SELECT "call_id","is_blacklisted","assigned_agent_id","fell_back" FROM "routing_log" '
                             'WHERE "call_id" = ANY(%s) ORDER BY "id"', (list(CALLS),), fetch=True)
            assert logs == [("it_route_bl", True, "it-vet", False), ("it_route_bl", True, "it-mid", True),
                            ("it_route_plain", False, None, False)]
            with pytest.raises(CallNotStartedError):
                await routing.route_call("it-no-such-call", ("it-vet",))
        finally:
            await reset()

    asyncio.run(scenario())
