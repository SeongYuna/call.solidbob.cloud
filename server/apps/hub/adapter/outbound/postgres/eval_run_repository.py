# Requirement: E-1, E-4, QUA-2
"""평가 실행 결과를 PostgreSQL 에 남긴다 (`eval_run` / `eval_result`).

**왜 필요한가.** [`CLAUDE.md` §5](https://github.com/solidbob02/call.solidbob.cloud/blob/main/CLAUDE.md):

> 값 하나에는 **언제·어느 커밋으로·어떤 명령으로·표본 몇 건**인지가 함께 남아야 한다.
> 넷 중 하나라도 채울 수 없으면 그 숫자는 아직 기록할 준비가 되지 않은 것이다.

터미널에만 찍힌 숫자는 **다음 실행에 덮여 사라진다.** 3주차에 골든셋을 150건으로 늘려
재측정할 때 «지난번보다 나아졌나» 를 물으려면 지난번 값이 남아 있어야 한다.

**이 모듈은 판정하지 않는다.** 기준선 미달 여부(절대 원칙 5)는 여기서 정하지 않고
하네스가 낸 `passed_absolute_rule` 을 **그대로 옮긴다.** 기록하는 쪽이 판정까지 하면
같은 규칙이 두 곳에 생긴다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .connection import ConnectionFactory

# 하네스 섹션명 → **기능 ID**. `eval_result.module` 은 VARCHAR(10) 이고 스키마 주석이
# 'B/C/C-5/F-2 등' 이라고 정해 뒀다 — 섹션명(`closure_gate` 12자)을 그대로 넣으면 잘린다.
# 기획서 기능 ID 를 그대로 쓰는 것은 `.claude/rules/rfp-harness.md §1` 규칙이기도 하다.
_MODULE_ID = {
    "domain_routing": "B-0",
    "trigger": "B-1",
    "retrieval": "B-2",
    "compliance": "C",
    "masking": "C-5",
    "closure_gate": "F-2",
    # 2026-09-09 추가. 없어서 `call_guard` 가 섹션명 그대로 들어갔고, **10자라 우연히
    # VARCHAR(10) 에 맞아** 에러 없이 통과했다 — 다른 행은 `B-2`·`C-5` 인데 이것만
    # 섹션명이었다(`_project/decisions/205`).
    "call_guard": "C-6",
    "voice_signal": "D-5",
    "asr": "A-5",
}

# 절대 규칙이 걸린 모듈만 `passed_absolute_rule` 을 채운다 — 그 외는 NULL 이다.
# db/schema.sql: COMMENT ON COLUMN "eval_result"."passed_absolute_rule" IS 'C-5·F-2만 해당'
_ABSOLUTE_RULE_MODULES = ("masking", "closure_gate")

_INSERT_RUN = """
INSERT INTO "eval_run"
    ("golden_set_version", "git_commit", "error_rate", "executed_at", "executed_by")
VALUES (%s, %s, %s, %s, %s)
RETURNING "run_id"
"""

_INSERT_RESULT = """
INSERT INTO "eval_result" ("run_id", "module", "metric_name", "metric_value", "passed_absolute_rule")
VALUES (%s, %s, %s, %s, %s)
"""


@dataclass(frozen=True)
class EvalRunRecord:
    """실행 1건의 재현 정보. **§5 가 요구하는 네 가지가 전부 필드로 있다.**

    `golden_set_version` = 어떤 표본 · `git_commit` = 어느 코드 · `executed_at` = 언제 ·
    각 지표의 `n` = 표본 몇 건. 「어떤 명령으로」는 골든셋 버전 + 커밋으로 재현된다.
    """

    golden_set_version: str
    git_commit: str | None = None
    error_rate: float = 0.0          # 4.2절 STT 오류 주입률. 지금은 주입 없음 → 0.0
    executed_by: str | None = None
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def flatten_report(report: dict) -> list[tuple[str, str, float, bool | None]]:
    """하네스 리포트를 `(module, metric_name, metric_value, passed_absolute_rule)` 로 편다.

    **「측정 불가 — 모듈 미구현」은 건너뛴다.** 미측정을 `0.0` 으로 적으면 «0점을 받았다» 와
    구분되지 않는다 — 절대 원칙 2·10 을 저장 계층에서 지키는 지점이다.
    `absolute_rule_passed` 같은 불리언은 지표가 아니므로 값 열에 넣지 않는다.
    모듈 이름은 **기능 ID** 로 바꿔 넣는다(`_MODULE_ID`) — 컬럼이 그 체계로 설계돼 있다.
    """
    rows: list[tuple[str, str, float, bool | None]] = []
    for module, result in report.items():
        if not isinstance(result, dict):      # 미구현 문자열
            continue
        passed = result.get("absolute_rule_passed") if module in _ABSOLUTE_RULE_MODULES else None
        module_id = _MODULE_ID.get(module, module)
        for name, value in result.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if value != value:                # NaN — 측정 불가다. 0 으로 적지 않는다
                continue
            rows.append((module_id, name, float(value), passed))
    return rows


class PostgresEvalRunRepository:
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def save(self, record: EvalRunRecord, report: dict) -> int:
        """실행 1건 + 지표들을 한 트랜잭션으로 남기고 `run_id` 를 돌려준다.

        지표가 하나도 없으면 (전부 미구현) **실행 자체를 남기지 않는다** — 빈 실행 기록은
        "돌렸는데 아무것도 못 쟀다" 를 "돌린 적 있다" 로 보이게 한다.
        """
        rows = flatten_report(report)
        if not rows:
            raise ValueError("기록할 지표가 없습니다 — 전부 '측정 불가'입니다")

        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    _INSERT_RUN,
                    (record.golden_set_version, record.git_commit, record.error_rate,
                     record.executed_at, record.executed_by),
                )
                run_id = (await cur.fetchone())[0]   # PostgreSQL 에는 lastrowid 가 없다
                await cur.executemany(
                    _INSERT_RESULT,
                    [(run_id, module, name, value, passed) for module, name, value, passed in rows],
                )
            await conn.commit()
        return int(run_id)
