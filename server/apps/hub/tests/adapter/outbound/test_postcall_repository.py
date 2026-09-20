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
            # 닫으면 통화도 끝난다(2026-09-20) — 전에는 요약만 남고 영원히 in_progress 였다
            closed = await _sql(connect, 'SELECT "status", "ended_at" FROM "call" WHERE "call_id"=%s', (CALL,))
            assert closed[0][0] == "closed" and closed[0][1] is not None
            first_end = closed[0][1]
            await repo.record(_draft("셋째 초안"))                     # 다시 닫아도
            again = await _sql(connect, 'SELECT "ended_at" FROM "call" WHERE "call_id"=%s', (CALL,))
            assert again[0][0] == first_end                            # 끝난 시각은 처음 닫은 때 그대로다
            await repo.record(_draft("둘째 초안", ["담당 부서에 전달해드리겠습니다"]))   # 아래 검사를 위해 되돌린다
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


# ─────────────────────────────── 가짜 커서 — DB 없이도 도는 모양 검사 (2026-09-20)

class _Cursor:
    def __init__(self, log, confirmed_at=None, exists=True):
        self._log, self._confirmed_at, self._exists = log, confirmed_at, exists

    async def execute(self, sql, args=None):
        self._log.append((" ".join(sql.split()), args))

    async def executemany(self, sql, rows):
        self._log.append((" ".join(sql.split()), rows))

    async def fetchone(self):
        return (self._confirmed_at,) if self._exists else None


def _fake_repo(log, **kw):
    from contextlib import asynccontextmanager

    class _Conn:
        @asynccontextmanager
        async def cursor(self):
            yield _Cursor(log, **kw)

        async def commit(self):
            log.append(("commit", None))

    @asynccontextmanager
    async def connect():
        yield _Conn()

    return PostgresPostcallRepository(connect)


def test_닫으면_통화도_끝난_것으로_적는다():
    """전에는 요약 초안만 쓰고 `status`·`ended_at` 을 아무도 안 건드려 끝난 통화가 영원히 `in_progress` 였다.

    09-17 로컬 E2E 24건 전부와 2026-09-20 운영 왕복에서 재현됐다. 같은 UPDATE·같은 트랜잭션에서 닫는다.
    """
    import asyncio

    log = []
    asyncio.run(_fake_repo(log).record(_draft("초안")))
    update = next(entry for entry in log if entry[0].startswith('UPDATE "call"'))
    sql, args = update
    assert '"status" = %s' in sql
    assert 'COALESCE("ended_at", %s)' in sql          # 다시 닫아도 처음 끝난 시각을 지킨다
    assert args[3] == "closed" and args[2] is not None  # (요약, 유형, 끝난 시각, 상태, call_id)
    assert log[-1][0] == "commit"


def test_확정된_통화는_닫는_UPDATE_까지_가지_않는다():
    """확정본 보호(409)가 먼저다 — 상태를 바꾸려다 확정 요약을 덮으면 안 된다."""
    import asyncio
    from datetime import datetime, timezone

    from hub.app.ports.output.postcall_record_port import SummaryAlreadyConfirmedError

    log = []
    with pytest.raises(SummaryAlreadyConfirmedError):
        asyncio.run(_fake_repo(log, confirmed_at=datetime.now(timezone.utc)).record(_draft("초안")))
    assert not any(entry[0].startswith('UPDATE "call"') for entry in log)
