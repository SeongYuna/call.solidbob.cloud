# Requirement: F-3, SEC-1
"""SQL 이 무엇을 묻는지와 행 → DTO 변환을 본다. 실제 스키마 대조는 integration 테스트.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from hub.adapter.outbound.postgres.briefing_facts_repository import PostgresBriefingFactsRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory

T = datetime(2026, 10, 6, 5, 0, tzinfo=timezone.utc)


class _Cursor:
    def __init__(self, script):
        self.script = list(script)   # 실행 순서대로 돌려줄 행
        self.calls = []

    async def execute(self, sql, args=None):
        self.calls.append((sql, args))

    async def fetchone(self):
        return self.script.pop(0)

    async def fetchall(self):
        return self.script.pop(0)


class _Ctx:
    def __init__(self, obj):
        self.obj = obj

    async def __aenter__(self):
        return self.obj

    async def __aexit__(self, *a):
        return False


class _Conn:
    def __init__(self, cur):
        self.cur = cur

    def cursor(self):
        return _Ctx(self.cur)


def _repo(script):
    cur = _Cursor(script)
    return PostgresBriefingFactsRepository(lambda: _Ctx(_Conn(cur))), cur


def _collect(repo, call_id):
    return asyncio.run(repo.collect(call_id))


def test_unknown_call_is_none():
    repo, _ = _repo([None])
    assert _collect(repo, "x") is None


def test_unidentified_customer_skips_history():
    repo, cur = _repo([(None, T)])
    facts = _collect(repo, "now")
    assert facts.customer_identified is False and facts.prior_calls == ()
    assert len(cur.calls) == 1


def test_prior_calls_exclude_current():
    p1 = ("p1", T - timedelta(days=1), "일반행정", "요약", T - timedelta(hours=20))
    repo, cur = _repo([
        ("hmac", T),                     # 이번 통화
        [p1],                            # 지난 통화
        [("p1", "회신 드리겠습니다")],     # 후속조치
        [("p1", "DASAN-TERM-4.1", "incomplete")],  # 절차별 마지막 판정
        [("p1", "insult")],              # 콜 가드
        (True,),                         # 블랙리스트
    ])
    facts = _collect(repo, "now")
    sql, args = cur.calls[1]
    assert '"call_id" <> %s' in sql and '"started_at" < %s' in sql and args == ("hmac", "now", T, 5)
    assert facts.customer_identified and facts.blacklisted
    pc = facts.prior_calls[0]
    assert pc.call_id == "p1" and pc.summary_confirmed is True
    assert pc.open_follow_ups == ("회신 드리겠습니다",)
    assert pc.incomplete_procedures == ("DASAN-TERM-4.1",)
    assert pc.call_guard_categories == ("insult",)


def test_completed_procedure_is_not_incomplete():
    p1 = ("p1", T - timedelta(days=1), None, None, None)
    repo, _ = _repo([("hmac", T), [p1], [], [("p1", "DASAN-TERM-4.1", "complete")], [], (False,)])
    facts = _collect(repo, "now")
    assert facts.prior_calls[0].incomplete_procedures == ()
    assert facts.prior_calls[0].summary_confirmed is False


def test_first_contact_has_no_followup_queries():
    repo, cur = _repo([("hmac", T), [], (False,)])
    facts = _collect(repo, "now")
    assert facts.customer_identified and facts.prior_calls == ()
    assert len(cur.calls) == 3   # 이번 통화 · 지난 통화 · 블랙리스트


CUST = "it-brief-cust-1006"
PRIOR = "it-brief-prior-1006"
NOW = "it-brief-now-1006"


@pytest.mark.integration
def test_실제_DB에서_절차별_마지막_판정과_후속조치를_읽는다(integration_settings):
    connect = build_connection_factory(integration_settings)

    async def sql(q, args=None):
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(q, args)
            await conn.commit()

    async def cleanup():
        for q in ['DELETE FROM "closure" WHERE "call_id" IN (%s, %s)',
                  'DELETE FROM "follow_up_action" WHERE "call_id" IN (%s, %s)',
                  'DELETE FROM "call" WHERE "call_id" IN (%s, %s)']:
            await sql(q, (PRIOR, NOW))
        await sql('DELETE FROM "customer" WHERE "customer_id" = %s', (CUST,))

    async def scenario():
        await cleanup()
        await sql('INSERT INTO "customer" ("customer_id","first_seen_at","status") VALUES (%s, now(), \'active\')', (CUST,))
        ins = ('INSERT INTO "call" ("call_id","domain","customer_id","started_at","channel_count","stt_engine","status") '
               "VALUES (%s, 'dasan', %s, now() - %s::interval, 1, 'mock', 'ended')")
        await sql(ins, (PRIOR, CUST, "1 day"))
        await sql(ins, (NOW, CUST, "0 seconds"))
        await sql('INSERT INTO "follow_up_action" ("call_id","action_text","status","created_at") '
                  "VALUES (%s, '회신 드리겠습니다', 'draft', now())", (PRIOR,))
        clo = ('INSERT INTO "closure" ("call_id","procedure","detected","verdict","decided_at") '
               "VALUES (%s, 'DASAN-TERM-4.1', true, %s, now() - %s::interval)")
        await sql(clo, (PRIOR, "incomplete", "2 hours"))
        await sql(clo, (PRIOR, "complete", "1 hour"))
        try:
            repo = PostgresBriefingFactsRepository(connect)
            facts = await repo.collect(NOW)
            assert facts.customer_identified and facts.blacklisted is False
            (pc,) = facts.prior_calls
            assert pc.call_id == PRIOR
            assert pc.incomplete_procedures == ()
            assert pc.open_follow_ups == ("회신 드리겠습니다",)
        finally:
            await cleanup()

    asyncio.run(scenario())
