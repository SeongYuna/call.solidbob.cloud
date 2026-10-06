# Requirement: F-3, E-1
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from briefing_check import score  # noqa: E402


def _r(sid, cat, source="model", run=1, expected="서류 보완"):
    return {"script": sid, "run": run, "expected": expected, "category": cat, "source": source}


def test_score_counts_matches_and_sources():
    s = score([_r("SYN-302", "서류 보완"), _r("SYN-304", "후속 확인", "rule", expected="컴플레인")])
    assert s["n"] == 2 and s["match"] == 1 and s["by_source"] == {"model": 1, "rule": 1}


def test_unstable_when_category_changes_across_runs():
    s = score([_r("SYN-302", "서류 보완", run=1), _r("SYN-302", "재문의", run=2)])
    assert s["unstable"] == ["SYN-302"]


def test_missing_category_is_a_miss_not_an_error():
    s = score([_r("SYN-302", None)])
    assert s["n"] == 1 and s["match"] == 0
