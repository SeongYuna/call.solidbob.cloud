# Requirement: J-2, J-4, SEC-1, QUA-1
"""블랙리스트 저장소 — 실제 PostgreSQL 로 요청 → 승인(등록) → 중복 거부 → 해제 → 재해제 거부를 한 흐름으로 본다.

근거 수집(`PostgresBlacklistEvidenceRepository`)도 같은 DB 에서 함께 본다 — 콜 가드 건수가 요청에 실리는가.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from blacklist.adapter.outbound.postgres_blacklist_repository import PostgresBlacklistRepository
from hub.app.dtos.blacklist_dto import BlacklistRequest
from hub.app.ports.output.blacklist_port import BlacklistConflict, BlacklistNotFound, UnknownAgent

REF = "c" * 64


@pytest.mark.integration
def test_실제_DB_요청부터_해제까지(integration_settings):
    from hub.adapter.outbound.postgres.blacklist_evidence_repository import PostgresBlacklistEvidenceRepository
    from hub.adapter.outbound.postgres.connection import build_connection_factory

    connect = build_connection_factory(integration_settings)
    calls = ("it_bl_1", "it_bl_2")

    async def reset():
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute('DELETE FROM "blacklist_entry" WHERE "customer_ref" = %s', (REF,))
                await cur.execute('DELETE FROM "blacklist_request" WHERE "customer_ref" = %s', (REF,))
                for call_id in calls:
                    await cur.execute('DELETE FROM "call_guard_flag" WHERE "call_id" = %s', (call_id,))
                    await cur.execute('DELETE FROM "transcript_segment" WHERE "call_id" = %s', (call_id,))
                    await cur.execute('DELETE FROM "call" WHERE "call_id" = %s', (call_id,))
                await cur.execute("""INSERT INTO "agent" ("agent_id", "display_name", "role") VALUES
                    ('it-agent', '상담원', 'agent'), ('it-admin', '관리자', 'admin') ON CONFLICT DO NOTHING""")
                await cur.execute('INSERT INTO "customer" VALUES (%s, NOW(), %s) ON CONFLICT DO NOTHING', (REF, "active"))
                for call_id in calls:
                    await cur.execute(
                        'INSERT INTO "call" (call_id, domain, customer_id, started_at, ended_at, channel_count, stt_engine, status)'
                        " VALUES (%s,'dasan',%s,NOW() - INTERVAL '10 minutes',NOW(),1,'google-stt','closed')",
                        (call_id, REF),
                    )
                await cur.execute("""INSERT INTO "transcript_segment" (segment_id, call_id, speaker, text, is_final, created_at)
                    VALUES (1, 'it_bl_1', 'customer', '여권 서류요', TRUE, NOW()),
                           (2, 'it_bl_1', 'customer', '이런 병신 같은', TRUE, NOW())""")
                await cur.execute("""INSERT INTO "call_guard_flag" (call_id, segment_id, category, phrase, span_start, span_end, detected_at)
                    VALUES ('it_bl_1', 2, 'insult', '병신', 3, 5, NOW())""")
            await conn.commit()

    async def scenario():
        await reset()
        collected = await PostgresBlacklistEvidenceRepository(connect).collect("it_bl_1")
        repo = PostgresBlacklistRepository(connect)

        def request(call_id, agent="it-agent"):
            return BlacklistRequest(request_id="", call_id=call_id, customer_ref=collected.customer_ref,
                                    requested_by=agent, reason="반복 폭언", context_excerpt=collected.context_excerpt,
                                    evidence=collected.evidence)

        with pytest.raises(UnknownAgent):
            await repo.save_request(request("it_bl_1", agent="nobody"))
        first = await repo.save_request(request("it_bl_1"))
        second = await repo.save_request(request("it_bl_2"))
        pending = [r.request_id for r in await repo.list_requests("pending")]

        expires = datetime.now(timezone.utc) + timedelta(days=30)
        approved = await repo.decide(first.request_id, approve=True, decided_by="it-admin", expires_at=expires, note="메모")
        with pytest.raises(BlacklistConflict):  # 이미 결정된 요청
            await repo.decide(first.request_id, approve=False, decided_by="it-admin", expires_at=None, note=None)
        with pytest.raises(BlacklistConflict):  # 같은 고객에 적용 중인 등록이 이미 있다
            await repo.decide(second.request_id, approve=True, decided_by="it-admin", expires_at=expires, note=None)
        with pytest.raises(BlacklistNotFound):
            await repo.decide("999999999", approve=False, decided_by="it-admin", expires_at=None, note=None)

        active = await repo.find_entry(REF)
        released = await repo.release_entry(active.entry_id, released_by="it-admin", reason="오인 신고")
        with pytest.raises(BlacklistConflict):
            await repo.release_entry(active.entry_id, released_by="it-admin", reason="다시")
        # 해제 뒤에는 같은 고객을 다시 등록할 수 있다 — 에피소드가 하나 더 생긴다
        await repo.decide(second.request_id, approve=True, decided_by="it-admin", expires_at=expires, note=None)
        entries = [e for e in await repo.list_entries() if e.customer_ref == REF]
        return collected, first, pending, approved, released, entries

    collected, first, pending, approved, released, entries = asyncio.run(scenario())
    assert collected.customer_ref == REF and collected.evidence.insult_count == 1
    assert collected.evidence.call_duration_s >= 590 and collected.context_excerpt == "이런 병신 같은"
    assert first.status == "pending" and first.request_id in pending
    assert approved.status == "approved" and approved.decided_by == "it-admin" and approved.decided_at is not None
    assert released.released_by == "it-admin" and released.release_reason == "오인 신고"
    assert len(entries) == 2 and sum(e.released_at is None for e in entries) == 1
