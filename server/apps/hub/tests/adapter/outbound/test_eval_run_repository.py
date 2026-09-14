# Requirement: E-1, E-4, QUA-2
"""평가 결과 기록. **미측정을 숫자로 바꾸지 않는 것**이 이 계층의 일이다.

`CLAUDE.md §5` — 값 하나에 언제·어느 커밋·어떤 표본인지가 함께 남아야 한다.
실제 DB 검증은 `@pytest.mark.integration` 으로 따로 둔다(기본 실행에서 빠진다).
"""

import asyncio
import math
from contextlib import asynccontextmanager

import pytest

from hub.adapter.outbound.postgres.eval_run_repository import (
    EvalRunRecord,
    PostgresEvalRunRepository,
    flatten_report,
)

REPORT = {
    "retrieval": {"recall_at_k": 0.857, "mrr": 0.702, "n": 14},
    "trigger": "측정 불가 — 모듈 미구현",
    "masking": {"miss_count": 0, "missed_items": [], "absolute_rule_passed": True,
                "over_masking_rate": math.nan, "n": 12},
    "closure_gate": {"accuracy": 1.0, "absolute_rule_passed": True, "failed_items": [], "n": 16},
}


# ── 평탄화 — 무엇을 남기고 무엇을 버리는가 ──────────────────────────────────

def test_미구현은_기록하지_않는다():
    """미측정을 `0.0` 으로 적으면 **'0점을 받았다'와 구분되지 않는다** (절대 원칙 2·10)."""
    modules = {m for m, *_ in flatten_report(REPORT)}
    assert "B-1" not in modules and "trigger" not in modules


def test_NaN_도_기록하지_않는다():
    """과잉 마스킹률은 음성 케이스가 없어 NaN 이다 — 잴 수 없는 것을 0 으로 적지 않는다."""
    names = {n for _, n, *_ in flatten_report(REPORT)}
    assert "over_masking_rate" not in names


def test_모듈_이름을_기능_ID_로_바꾼다():
    """`eval_result.module` 은 VARCHAR(10) 이고 스키마 주석이 'B/C/C-5/F-2 등' 이다.
    섹션명(`closure_gate` 12자)을 그대로 넣으면 **DB 에서 잘린다** — 실제로 겪었다."""
    modules = {m for m, *_ in flatten_report(REPORT)}
    assert modules == {"B-2", "C-5", "F-2"}
    assert all(len(m) <= 10 for m in modules)


def test_절대_규칙_모듈만_통과여부를_채운다():
    """스키마: passed_absolute_rule 은 'C-5·F-2만 해당, 그 외 NULL'."""
    passed = {m: p for m, _, _, p in flatten_report(REPORT)}
    assert passed["C-5"] is True and passed["F-2"] is True
    assert passed["B-2"] is None


def test_불리언은_지표값으로_넣지_않는다():
    """`absolute_rule_passed` 는 판정이지 측정값이 아니다 — 1.0 으로 섞이면 지표가 오염된다."""
    names = {n for _, n, *_ in flatten_report(REPORT)}
    assert "absolute_rule_passed" not in names


# ── 저장 ───────────────────────────────────────────────────────────────────

class _FakeCursor:
    def __init__(self, log): self._log = log
    async def execute(self, sql, args=None): self._log.append(("execute", args))
    async def executemany(self, sql, args): self._log.append(("executemany", args))
    async def fetchone(self): return (77,)


class _FakeConnection:
    def __init__(self, log): self._log = log
    @asynccontextmanager
    async def cursor(self): yield _FakeCursor(self._log)
    async def commit(self): self._log.append(("commit", None))


def _run(report=REPORT):
    log = []

    @asynccontextmanager
    async def connect(): yield _FakeConnection(log)

    repo = PostgresEvalRunRepository(connect)
    run_id = asyncio.run(repo.save(EvalRunRecord(golden_set_version="v1-50", git_commit="abc123"), report))
    return run_id, log


def test_재현_정보를_함께_남긴다():
    """§5 — 언제·어느 커밋·어떤 표본. 넷 중 하나라도 없으면 기록할 준비가 안 된 숫자다."""
    _, log = _run()
    args = log[0][1]
    assert args[0] == "v1-50" and args[1] == "abc123"
    assert args[3] is not None          # executed_at


def test_run_id_를_돌려준다():
    """PostgreSQL 에는 lastrowid 가 없다 — RETURNING 으로 받는다."""
    run_id, _ = _run()
    assert run_id == 77


def test_지표가_하나도_없으면_실행을_남기지_않는다():
    """빈 실행 기록은 **'돌렸는데 아무것도 못 쟀다'를 '돌린 적 있다'로 보이게 한다.**"""
    with pytest.raises(ValueError):
        _run({"retrieval": "측정 불가 — 모듈 미구현"})


def test_판정하지_않고_그대로_옮긴다():
    """기준선 미달 여부는 하네스가 정한다 — 기록하는 쪽이 판정하면 규칙이 두 곳에 생긴다."""
    _, log = _run({**REPORT, "masking": {**REPORT["masking"], "absolute_rule_passed": False}})
    rows = log[1][1]
    assert any(r[1] == "C-5" and r[4] is False for r in rows)


# ── 실제 PostgreSQL (기본 실행에서 제외) ────────────────────────────────────
#    cd infra && docker compose up -d
#    cd ../server && ../.venv/bin/python -m pytest -m integration
#    DB 는 `integration_settings` 픽스처(server/conftest.py)가 준다.


@pytest.mark.integration
def test_실제_DB에_기록되고_컬럼_길이에_들어간다(integration_settings):
    """가짜 커서는 VARCHAR(10) 초과를 통과시킨다 — 실제로 그것 때문에 한 번 깨졌다."""
    from hub.adapter.outbound.postgres.connection import build_connection_factory

    connect = build_connection_factory(integration_settings)
    repo = PostgresEvalRunRepository(connect)

    async def scenario():
        run_id = await repo.save(
            EvalRunRecord(golden_set_version="it-test", git_commit="0" * 40, executed_by="pytest"),
            REPORT,
        )
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    'SELECT "module", "metric_name", "metric_value", "passed_absolute_rule"'
                    ' FROM "eval_result" WHERE "run_id" = %s ORDER BY "module", "metric_name"',
                    (run_id,))
                rows = await cur.fetchall()
                assert {r[0] for r in rows} == {"B-2", "C-5", "F-2"}
                assert any(r[0] == "C-5" and r[3] is True for r in rows)
                await cur.execute('DELETE FROM "eval_result" WHERE "run_id" = %s', (run_id,))
                await cur.execute('DELETE FROM "eval_run" WHERE "run_id" = %s', (run_id,))
            await conn.commit()

    asyncio.run(scenario())
