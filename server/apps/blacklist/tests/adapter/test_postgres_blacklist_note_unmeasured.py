# Requirement: J-2, J-4, D-5, SEC-1, QUA-1
"""`decisions/316` — 실제 PostgreSQL 에서:

- D-5 판정이 붙지 않았으면 온도 이상은 0 이 아니라 **NULL(미측정)** 로 저장되고 그대로 읽힌다
- 붙었다고 켜면(`voice_outliers_wired=True`) `voice_outlier` 건수를 센다 — 0 이면 진짜 0 이다
- 반려 사유는 요청 행(`decision_note`)에, 승인 메모는 등록(`blacklist_entry.note`)에 — 한 벌만

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from blacklist.adapter.outbound.postgres_blacklist_repository import PostgresBlacklistRepository
from hub.app.dtos.blacklist_dto import BlacklistRequest

REF = "d" * 64
CALLS = ("it_316_a", "it_316_b")


@pytest.mark.integration
def test_미측정은_NULL로_남고_반려_사유는_요청에_남는다(integration_settings):
    from hub.adapter.outbound.postgres.blacklist_evidence_repository import PostgresBlacklistEvidenceRepository
    from hub.adapter.outbound.postgres.connection import build_connection_factory

    connect = build_connection_factory(integration_settings)

    async def sql(q, args=None, fetch=False):
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(q, args)
                rows = await cur.fetchall() if fetch else None
            await conn.commit()
        return rows

    async def reset():
        await sql('DELETE FROM "blacklist_entry" WHERE "customer_ref" = %s', (REF,))
        await sql('DELETE FROM "blacklist_request" WHERE "customer_ref" = %s', (REF,))
        for call_id in CALLS:
            await sql('DELETE FROM "call" WHERE "call_id" = %s', (call_id,))

    async def scenario():
        await reset()
        await sql("""INSERT INTO "agent" ("agent_id","display_name","role") VALUES ('it-316-agent','상담원','agent'),
                     ('it-316-admin','관리자','admin') ON CONFLICT DO NOTHING""")
        await sql('INSERT INTO "customer" VALUES (%s, NOW(), %s) ON CONFLICT DO NOTHING', (REF, "active"))
        for call_id in CALLS:
            await sql("INSERT INTO \"call\" (call_id, domain, customer_id, started_at, channel_count, stt_engine, status) "
                      "VALUES (%s,'dasan',%s,NOW(),1,'mock','closed')", (call_id, REF))
        try:
            unwired = await PostgresBlacklistEvidenceRepository(connect).collect(CALLS[0])
            wired = await PostgresBlacklistEvidenceRepository(connect, voice_outliers_wired=True).collect(CALLS[0])
            assert unwired.evidence.temperature_outliers is None  # 미측정
            assert wired.evidence.temperature_outliers == 0       # 판정이 붙었다면 진짜 0

            repo = PostgresBlacklistRepository(connect)

            def request(call_id):
                return BlacklistRequest(request_id="", call_id=call_id, customer_ref=REF, requested_by="it-316-agent",
                                        reason="반복 폭언", context_excerpt="자막", evidence=unwired.evidence)

            a = await repo.save_request(request(CALLS[0]))
            b = await repo.save_request(request(CALLS[1]))
            assert a.evidence.temperature_outliers is None  # NULL 로 저장되고 NULL 로 읽힌다

            rejected = await repo.decide(a.request_id, approve=False, decided_by="it-316-admin", expires_at=None,
                                         note="통화 기록상 폭언 아님")
            approved = await repo.decide(b.request_id, approve=True, decided_by="it-316-admin",
                                         expires_at=datetime.now(timezone.utc) + timedelta(days=30), note="승인 메모")
            assert rejected.decision_note == "통화 기록상 폭언 아님"
            assert approved.decision_note is None  # 승인 메모는 요청 행에 두 벌 남기지 않는다
            assert (await repo.find_entry(REF)).note == "승인 메모"
            listed = {r.request_id: r for r in await repo.list_requests()}
            assert listed[a.request_id].decision_note == "통화 기록상 폭언 아님"
            # 「내 요청」 — 요청자로 거른다(`w6-agent-my-requests-api`)
            mine = {r.request_id for r in await repo.list_requests(requested_by="it-316-agent")}
            assert {a.request_id, b.request_id} <= mine
            assert await repo.list_requests(requested_by="it-316-admin") == []
            assert [r.request_id for r in await repo.list_requests("rejected", requested_by="it-316-agent")
                    if r.request_id in (a.request_id, b.request_id)] == [a.request_id]
        finally:
            await reset()

    asyncio.run(scenario())
