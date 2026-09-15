# Requirement: J-4, SEC-1, QUA-1
"""만료 연장·단축과 이력(`decisions/309`) · 만료된 등록이 같은 고객의 새 승인을 막지 않는다 — 실제 PostgreSQL.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from blacklist.adapter.outbound.postgres_blacklist_repository import EXPIRED_RELEASE_REASON, PostgresBlacklistRepository
from hub.app.dtos.blacklist_dto import BlacklistRequest, RequestEvidence
from hub.app.ports.output.blacklist_port import BlacklistConflict, BlacklistNotFound, ExpiryBeyondCap

REF = "e" * 64
CALLS = ("it_exp_1", "it_exp_2")


def _request(call_id):
    return BlacklistRequest(request_id="", call_id=call_id, customer_ref=REF, requested_by="it-exp-agent", reason="반복 폭언",
                            context_excerpt="…", evidence=RequestEvidence(call_duration_s=60, insult_count=1, threat_count=0,
                                                                          sexual_count=0, temperature_outliers=0))


@pytest.mark.integration
def test_실제_DB_만료_연장_단축_이력과_만료_뒤_재승인(integration_settings):
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
        await sql('DELETE FROM "blacklist_entry_expiry_change" WHERE "entry_id" IN '
                  '(SELECT "entry_id" FROM "blacklist_entry" WHERE "customer_ref" = %s)', (REF,))
        await sql('DELETE FROM "blacklist_entry" WHERE "customer_ref" = %s', (REF,))
        await sql('DELETE FROM "blacklist_request" WHERE "customer_ref" = %s', (REF,))
        for call_id in CALLS:
            await sql('DELETE FROM "call" WHERE "call_id" = %s', (call_id,))

    async def scenario():
        await reset()
        await sql("""INSERT INTO "agent" ("agent_id", "display_name", "role") VALUES
            ('it-exp-agent', '상담원', 'agent'), ('it-exp-admin', '관리자', 'admin') ON CONFLICT DO NOTHING""")
        await sql('INSERT INTO "customer" VALUES (%s, NOW(), %s) ON CONFLICT DO NOTHING', (REF, "active"))
        for call_id in CALLS:
            await sql('INSERT INTO "call" (call_id, domain, customer_id, started_at, channel_count, stt_engine, status)'
                      " VALUES (%s,'dasan',%s,NOW(),1,'mock','closed')", (call_id, REF))
        now = datetime.now(timezone.utc)
        repo = PostgresBlacklistRepository(connect, now=lambda: now)
        try:
            first = await repo.save_request(_request(CALLS[0]))
            await repo.decide(first.request_id, approve=True, decided_by="it-exp-admin", expires_at=now + timedelta(days=30), note=None)
            (entry,) = [e for e in await repo.list_entries() if e.customer_ref == REF]

            # 연장 → 단축: 이전·새 값이 이력에 둘 다 남는다
            extended, c1 = await repo.change_expiry(entry.entry_id, changed_by="it-exp-admin", expires_at=now + timedelta(days=180), reason="재발")
            shortened, c2 = await repo.change_expiry(entry.entry_id, changed_by="it-exp-admin", expires_at=now + timedelta(days=7), reason="오인 일부")
            assert extended.expires_at == now + timedelta(days=180) and shortened.expires_at == now + timedelta(days=7)
            assert (c1.previous_expires_at, c1.new_expires_at) == (now + timedelta(days=30), now + timedelta(days=180))
            assert (c2.previous_expires_at, c2.new_expires_at) == (now + timedelta(days=180), now + timedelta(days=7))
            assert [c.change_id for c in await repo.list_expiry_changes(entry.entry_id)] == [c1.change_id, c2.change_id]

            # 누적 상한: 승인일 + 365일까지만 — 넘으면 거부되고 만료·이력은 그대로다
            with pytest.raises(ExpiryBeyondCap):
                await repo.change_expiry(entry.entry_id, changed_by="it-exp-admin", expires_at=now + timedelta(days=366), reason="과한 연장")
            assert len(await repo.list_expiry_changes(entry.entry_id)) == 2
            assert [e for e in await repo.list_entries() if e.entry_id == entry.entry_id][0].expires_at == now + timedelta(days=7)

            with pytest.raises(BlacklistNotFound):
                await repo.change_expiry(999999999, changed_by="it-exp-admin", expires_at=now, reason="x")
            with pytest.raises(BlacklistNotFound):
                await repo.list_expiry_changes(999999999)

            # 만료시킨다(시계를 40일 뒤로) → 해제 안 된 채 만료된 등록이 같은 고객의 새 승인을 막지 않아야 한다
            later = now + timedelta(days=40)
            later_repo = PostgresBlacklistRepository(connect, now=lambda: later)
            second = await later_repo.save_request(_request(CALLS[1]))
            await later_repo.decide(second.request_id, approve=True, decided_by="it-exp-admin",
                                    expires_at=later + timedelta(days=30), note=None)
            rows = await sql('SELECT "entry_id", "released_at", "released_by", "release_reason" FROM "blacklist_entry" '
                             'WHERE "customer_ref" = %s ORDER BY "entry_id"', (REF,), fetch=True)
            (old_id, old_released_at, old_by, old_reason), (_, new_released_at, _, _) = rows
            assert old_id == entry.entry_id
            assert old_released_at == now + timedelta(days=7)  # 실제로 끝난 시각 = 만료 시각
            assert old_by is None and old_reason == EXPIRED_RELEASE_REASON  # 사람이 푼 것이 아니다
            assert new_released_at is None

            with pytest.raises(BlacklistConflict):  # 닫힌 등록은 만료를 바꿀 수 없다
                await later_repo.change_expiry(entry.entry_id, changed_by="it-exp-admin", expires_at=later, reason="x")
        finally:
            await reset()

    asyncio.run(scenario())
