# Requirement: SEC-1, QUA-2
"""배포 전 스키마 대조(`decisions/128`, `w6-deploy-schema-precheck`) — 멈춰야 할 때 멈추고, 잘린 덤프로 판정하지 않는다."""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "compare_prod_schema.py"

SCHEMA = '''CREATE TABLE "call" (
    "call_id" VARCHAR(40) NOT NULL,
    "status" VARCHAR(20) NOT NULL,
    PRIMARY KEY ("call_id")
);
CREATE TABLE "blacklist_request" (
    "request_id" BIGINT NOT NULL,
    "decision_note" VARCHAR(500) NULL,
    PRIMARY KEY ("request_id")
);
'''

SAME = [
    "call|call_id|varchar|NO|40|-1|-1",
    "call|status|varchar|NO|20|-1|-1",
    "blacklist_request|request_id|int8|NO|-1|64|0",
    "blacklist_request|decision_note|varchar|YES|500|-1|-1",
]


def _run(tmp_path, rows, *extra, declared=None):
    schema = tmp_path / "schema.sql"
    schema.write_text(SCHEMA, encoding="utf-8")
    dump = tmp_path / "prod.txt"
    n = len(rows) if declared is None else declared
    dump.write_text("ROWS %d\n" % n + "\n".join(rows) + "\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(dump), "--schema", str(schema), *extra],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def test_같으면_통과한다(tmp_path):
    code, out = _run(tmp_path, SAME)
    assert code == 0 and "어긋남 0" in out


def test_마이그레이션을_안_넣었으면_멈춘다(tmp_path):
    """09-22 PR #111 — decision_note 가 운영에 없는 채로 서버가 먼저 나갔다(11분간 500)."""
    code, out = _run(tmp_path, SAME[:3], "--allow-prod-extra")
    assert code == 1 and "decision_note" in out and "마이그레이션 미적용" in out


def test_타입이_다르면_멈춘다(tmp_path):
    rows = SAME[:1] + ["call|status|text|NO|-1|-1|-1"] + SAME[2:]
    code, out = _run(tmp_path, rows, "--allow-prod-extra")
    assert code == 1 and "🔴" in out


def test_운영에만_있는_컬럼은_배포_대조에서_경고만(tmp_path):
    rows = SAME + ["call|legacy_flag|bool|YES|-1|-1|-1"]
    strict, _ = _run(tmp_path, rows)
    loose, out = _run(tmp_path, rows, "--allow-prod-extra")
    assert strict == 1  # 손으로 돌릴 때(기본)는 어긋남으로 센다
    assert loose == 0 and "경고만" in out


def test_잘린_덤프로는_판정하지_않는다(tmp_path):
    """SSM 표준 출력은 24,000자에서 잘린다 — 머리말 행 수와 다르면 멈춘다."""
    code, out = _run(tmp_path, SAME[:2], "--allow-prod-extra", declared=4)
    assert code == 1 and "불완전" in out
