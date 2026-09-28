# Requirement: F-2, C-5
"""`decisions/219` 집계(`procedure_counts`·`procedure_summary`)와 보류 표본 생성기의 가짜 개인정보 검사 — 스택 없이 돈다."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from e2e.judge import Verdict, procedure_counts  # noqa: E402
from e2e.report import procedure_summary, to_json  # noqa: E402
from generate_dasan_v1_holdout import build, fake_pii_errors  # noqa: E402
from scenarios_v1_holdout import SCRIPTS  # noqa: E402

NEEDED = {"procedure": {"doc_ids": ["DASAN-TERM-4.6", "DASAN-MANUAL-3.3"], "required_documents": ["사진"]}}
NO_DOCS = {"procedure": {"doc_ids": ["DASAN-MANUAL-2.2"], "required_documents": []}}


def _record(*procs: str) -> dict:
    return {"closures": [{"closure_id": i, "procedure": p, "verdict": "incomplete"} for i, p in enumerate(procs, 1)]}


def test_counts_wrong_rows_per_procedure_and_needed_hit():
    got = procedure_counts(NEEDED, _record("DASAN-TERM-4.6", "DASAN-TERM-4.13", "DASAN-TERM-4.13", "DASAN-TERM-3.8"))
    assert got == {"wrong": {"DASAN-TERM-3.8": 1, "DASAN-TERM-4.13": 2}, "needed": True}


def test_needed_is_false_when_only_wrong_procedures_and_none_for_no_doc_scripts():
    assert procedure_counts(NEEDED, _record("DASAN-TERM-4.13"))["needed"] is False
    assert procedure_counts(NO_DOCS, _record("DASAN-TERM-4.13")) == {"wrong": {"DASAN-TERM-4.13": 1}, "needed": None}


def test_summary_sums_pairs_rows_and_lists_missed_needed():
    a = Verdict("SYN-101", "c1", procedures=procedure_counts(NEEDED, _record("DASAN-TERM-4.13", "DASAN-TERM-4.13")))
    b = Verdict("SYN-109", "c2", procedures=procedure_counts(NO_DOCS, _record("DASAN-TERM-2.9")))
    c = Verdict("SYN-102", "c3", procedures=procedure_counts(NEEDED, _record("DASAN-TERM-4.6")))
    s = procedure_summary([a, b, c])
    assert s == {"wrong_pairs": 2, "wrong_rows": 3, "scripts_with_wrong": 2, "needed_scripts": 2, "needed_hit": 1,
                 "needed_missed": ["SYN-101"]}
    assert json.loads(to_json({}, [a, b, c]))["summary"]["procedures"]["wrong_rows"] == 3


def test_fake_pii_check_accepts_v0_style_values_and_rejects_real_looking_ones():
    assert fake_pii_errors("P4", "010-0000-0206") == []
    assert fake_pii_errors("P4", "공일공 공공공공 공일일육") == []
    assert fake_pii_errors("P1", "4501011000000") == []
    assert fake_pii_errors("P2", "9410 0000 0000 0121") == []
    assert fake_pii_errors("P3", "000000204204") == []
    assert fake_pii_errors("P7", "한별시 누리구 솔바람로 31, 402호") == []
    assert fake_pii_errors("P4", "010-1234-5678")
    assert fake_pii_errors("P2", "4111 1111 1111 1111")  # Luhn 통과 — 실존할 수 있는 형식
    assert fake_pii_errors("P7", "서울시 중구 세종대로 110")


def test_holdout_scripts_build_without_errors_and_match_committed_json():
    for s in SCRIPTS:
        doc, errors = build(s)
        assert errors == [], errors
        committed = json.loads((HERE / "dasan-v1-holdout" / f"{doc['id']}.json").read_text(encoding="utf-8"))
        assert committed == doc, f"{doc['id']} JSON 이 생성기와 다르다 — 손으로 고치지 말고 다시 생성한다"
