# Requirement: J-4, SEC-1, QUA-1
"""보존 기간 정리(`decisions/312`) — 실제 PostgreSQL: 끝난 지 180일 지난 것만 · 행은 남고 문장만 표시로 · 두 번 불러도 같다.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from blacklist.adapter.outbound.postgres_blacklist_repository import PostgresBlacklistRepository
from blacklist.domain.services.retention import PURGED_TEXT
from hub.app.dtos.blacklist_dto import BlacklistRequest, RequestEvidence

OLD, FRESH = "a" * 64, "b" * 64


def _request(call_id, ref):
    return BlacklistRequest(request_id="", call_id=call_id, customer_ref=ref, requested_by="it-ret-agent", reason="폭언 사유",
                            context_excerpt="자막 발췌", evidence=RequestEvidence(call_duration_s=1, insult_count=1,
                                                                              threat_count=0, sexual_count=0, temperature_outliers=0))


@pytest.mark.integration
def test_실제_DB_보존_기간_정리(integration_settings):
    from hub.adapter.outbound.postgres.connection import build_connection_factory

    connect = build_connection_factory(integration_settings)
    calls = {"it_ret_old_a": OLD, "it_ret_old_r": OLD, "it_ret_new_a": FRESH, "it_ret_new_r": FRESH}

    async def sql(q, args=None, fetch=False):
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(q, args)
                rows = await cur.fetchall() if fetch else None
            await conn.commit()
        return rows

    async def reset():
        for ref in (OLD, FRESH):
            await sql('DELETE FROM "blacklist_entry_expiry_change" WHERE "entry_id" IN (SELECT "entry_id" FROM "blacklist_entry" WHERE "customer_ref" = %s)', (ref,))
            await sql('DELETE FROM "blacklist_entry" WHERE "customer_ref" = %s', (ref,))
            await sql('DELETE FROM "blacklist_request" WHERE "customer_ref" = %s', (ref,))
        for call_id in calls:
            await sql('DELETE FROM "call" WHERE "call_id" = %s', (call_id,))

    async def scenario():
        await reset()
        await sql("""INSERT INTO "agent" ("agent_id","display_name","role") VALUES ('it-ret-agent','상담원','agent'),
                     ('it-ret-admin','관리자','admin') ON CONFLICT DO NOTHING""")
        for ref in (OLD, FRESH):
            await sql('INSERT INTO "customer" VALUES (%s, NOW(), %s) ON CONFLICT DO NOTHING', (ref, "active"))
        for call_id, ref in calls.items():
            await sql("INSERT INTO \"call\" (call_id, domain, customer_id, started_at, channel_count, stt_engine, status) "
                      "VALUES (%s,'dasan',%s,NOW(),1,'mock','closed')", (call_id, ref))
        try:
            long_ago = datetime.now(timezone.utc) - timedelta(days=400)
            past = PostgresBlacklistRepository(connect, now=lambda: long_ago)
            recent = PostgresBlacklistRepository(connect)  # 지금

            # 오래전: 승인 → 연장 → 해제(400일 전) · 반려(400일 전)
            a = await past.save_request(_request("it_ret_old_a", OLD))
            await past.decide(a.request_id, approve=True, decided_by="it-ret-admin", expires_at=long_ago + timedelta(days=30), note=None)
            (old_entry,) = [e for e in await past.list_entries() if e.customer_ref == OLD]
            await past.change_expiry(old_entry.entry_id, changed_by="it-ret-admin", expires_at=long_ago + timedelta(days=60), reason="오래된 연장 사유")
            await past.release_entry(old_entry.entry_id, released_by="it-ret-admin", reason="해제")
            r_old = await past.save_request(_request("it_ret_old_r", OLD))
            await past.decide(r_old.request_id, approve=False, decided_by="it-ret-admin", expires_at=None, note=None)

            # 최근: 승인 → 연장(진행 중) · 반려(방금)
            b = await recent.save_request(_request("it_ret_new_a", FRESH))
            await recent.decide(b.request_id, approve=True, decided_by="it-ret-admin", expires_at=datetime.now(timezone.utc) + timedelta(days=30), note=None)
            (new_entry,) = [e for e in await recent.list_entries() if e.customer_ref == FRESH]
            await recent.change_expiry(new_entry.entry_id, changed_by="it-ret-admin", expires_at=datetime.now(timezone.utc) + timedelta(days=60), reason="최근 연장 사유")
            r_new = await recent.save_request(_request("it_ret_new_r", FRESH))
            await recent.decide(r_new.request_id, approve=False, decided_by="it-ret-admin", expires_at=None, note=None)

            first = await recent.purge_retained_texts()
            assert first.retention_days == 180
            assert (first.expiry_change_reasons_purged, first.rejected_requests_purged) >= (1, 1)

            assert [c.reason for c in await recent.list_expiry_changes(old_entry.entry_id)] == [PURGED_TEXT]
            assert [c.reason for c in await recent.list_expiry_changes(new_entry.entry_id)] == ["최근 연장 사유"]  # 끝나지 않았다
            rows = dict(((rid, (reason, excerpt)) for rid, reason, excerpt in await sql(
                'SELECT "request_id","reason","context_excerpt" FROM "blacklist_request" WHERE "request_id" = ANY(%s)',
                ([int(r_old.request_id), int(r_new.request_id), int(a.request_id)],), fetch=True)))
            assert rows[int(r_old.request_id)] == (PURGED_TEXT, PURGED_TEXT)  # 반려 400일 전 — 비움
            assert rows[int(r_new.request_id)] == ("폭언 사유", "자막 발췌")  # 방금 반려 — 남김
            assert rows[int(a.request_id)] == ("폭언 사유", "자막 발췌")  # 승인된 요청은 이 정리의 대상이 아니다

            again = await recent.purge_retained_texts()  # 멱등
            old_only = [c for c in await recent.list_expiry_changes(old_entry.entry_id)]
            assert old_only[0].reason == PURGED_TEXT and again.cutoff <= datetime.now(timezone.utc)
        finally:
            await reset()

    asyncio.run(scenario())
