# Requirement: D-1, D-2, D-3, QUA-1
"""통화 후 초안 저장 — 실제 PostgreSQL(현재 db/schema.sql)에서: 초안 교체 · 확정본 보호 · 없는 통화.

    cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration
"""

import asyncio

import pytest

from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.postcall_repository import DRAFT_STATUS, PostgresPostcallRepository
from hub.app.dtos.call_summary_dto import CallSummaryDraft, FollowUpAction
from hub.app.ports.output.postcall_record_port import SummaryAlreadyConfirmedError
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

CALL = "it-postcall-0915"


async def _sql(connect, sql, args=None):
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall() if cur.description else None
        await conn.commit()
    return rows


def _draft(summary, actions=()):
    return CallSummaryDraft(call_id=CALL, summary_text=summary, inquiry_type=None,
                            follow_up_actions=tuple(FollowUpAction(action_text=a) for a in actions))


@pytest.mark.integration
def test_실제_DB에서_초안은_교체되고_확정본은_덮지_않는다(integration_settings):
    connect = build_connection_factory(integration_settings)
    repo = PostgresPostcallRepository(connect)

    async def cleanup():
        await _sql(connect, 'DELETE FROM "follow_up_action" WHERE "call_id" = %s', (CALL,))
        await _sql(connect, 'DELETE FROM "call" WHERE "call_id" = %s', (CALL,))

    async def scenario():
        await cleanup()
        await _sql(connect, 'INSERT INTO "call" ("call_id","domain","started_at","channel_count","stt_engine","status") '
                            "VALUES (%s, 'dasan', now(), 1, 'mock', 'in_progress')", (CALL,))
        try:
            await repo.record(_draft("첫 초안", ["문자로 보내 드리겠습니다", "회신 드리겠습니다"]))
            await repo.record(_draft("둘째 초안", ["담당 부서에 전달해드리겠습니다"]))

            call = await _sql(connect, 'SELECT "summary_text","inquiry_type","summary_confirmed_at" FROM "call" WHERE "call_id"=%s', (CALL,))
            assert call == [("둘째 초안", None, None)]  # 확정 시각은 건드리지 않는다 — NULL 이 곧 초안
            actions = await _sql(connect, 'SELECT "action_text","status" FROM "follow_up_action" WHERE "call_id"=%s', (CALL,))
            assert actions == [("담당 부서에 전달해드리겠습니다", DRAFT_STATUS)]  # 앞 초안의 두 건은 교체됐다

            # 상담원이 손댄(초안이 아닌) 항목은 다시 닫아도 남는다
            await _sql(connect, 'INSERT INTO "follow_up_action" ("call_id","action_text","status","created_at") '
                                "VALUES (%s, '상담원이 적은 할 일', 'open', now())", (CALL,))
            await repo.record(_draft("셋째 초안"))
            left = await _sql(connect, 'SELECT "action_text" FROM "follow_up_action" WHERE "call_id"=%s', (CALL,))
            assert left == [("상담원이 적은 할 일",)]

            await _sql(connect, 'UPDATE "call" SET "summary_confirmed_at" = now() WHERE "call_id"=%s', (CALL,))
            with pytest.raises(SummaryAlreadyConfirmedError):
                await repo.record(_draft("확정 뒤 초안"))
            still = await _sql(connect, 'SELECT "summary_text" FROM "call" WHERE "call_id"=%s', (CALL,))
            assert still == [("셋째 초안",)]

            with pytest.raises(CallNotStartedError):
                await repo.record(CallSummaryDraft(call_id="it-no-such-call", summary_text="x"))
        finally:
            await cleanup()

    asyncio.run(scenario())
