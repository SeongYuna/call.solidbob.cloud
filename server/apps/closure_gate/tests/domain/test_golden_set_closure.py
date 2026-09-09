# Requirement: F-2, QUA-2
"""골든셋 F-2 케이스 회귀 — **오판정은 1건이라도 실패**다.

[6.2절](/docs/06/)이 정한 대로 평균이 아니라 건 단위로 본다. 채점은 규칙 기반이다
(절대 원칙 1) — 기대한 `verdict`·`missing`·`source` 와 정확히 같은지만 본다.

단위 테스트는 내가 상상한 조합을 보지만, 이 테스트는 **팀이 정답을 붙인 케이스**를 본다.
"""

import json
from pathlib import Path

import pytest

from closure_gate.adapter.outbound.rule_closure_gate_adapter import RuleClosureGateAdapter

GOLDEN_SET = Path(__file__).resolve().parents[4].parent / "golden-set" / "v1-50.json"


def _f2_cases():
    if not GOLDEN_SET.exists():
        return []
    raw = json.loads(GOLDEN_SET.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else raw.get("cases", raw.get("items", []))
    return [pytest.param(c["id"], c["f2_case"], id=c["id"])
            for c in items if c.get("f2_case")]


CASES = _f2_cases()


def test_골든셋에_F2_케이스가_실려있다():
    """케이스가 0건이면 아래 테스트가 전부 통과해버린다 — 빈 채로 초록불이 되는 것을 막는다.

    ⚠ **2026-08-28 현재 케이스가 0건이다.** 다산콜센터 단일 도메인으로 전환하면서
    (`_project/decisions/201`) F-2 케이스를 갖고 있던 금융보험·쇼핑 항목이 빠졌다.
    다산은 정보 안내형이라 종결 처리 유형이 없다(`knowledge-base/dasan/policy/POLICY.md`).

    **`decisions/201` 은 F-2 게이트를 「필요서류 체크리스트」로 전용하기로 했다** —
    필수 항목을 규칙으로 정의하고 빠진 것을 `missing` 으로 돌려주는 구조가 같다.
    그 케이스가 만들어지면 이 skip 을 지운다.

    통과가 아니라 **skip 으로 둔 이유**: `assert CASES` 로 두면 스위트가 빨간불이라 다른
    회귀를 못 보고, 조건을 지우면 0건인 채로 초록불이 된다. skip 은 "지금 안 재고 있다"를
    출력에 남긴다.
    """
    assert GOLDEN_SET.exists(), f"골든셋이 없다: {GOLDEN_SET}"
    if not CASES:
        pytest.skip(
            "F-2 케이스 0건 — 다산 단일 도메인 전환(decisions/201). "
            "필요서류 체크리스트로 전용하면서 케이스를 만든다"
        )


@pytest.mark.parametrize("case_id, case", CASES)
def test_골든셋_판정이_정확히_일치한다(case_id, case):
    v = RuleClosureGateAdapter().evaluate(case_id, case["closure_type"], case["evidence"])

    assert v.verdict == case["expected_verdict"], (
        f"{case_id}: 판정이 다르다 — F-2 절대 규칙\n"
        f"  처리유형: {case['closure_type']}  근거: {case['evidence']}\n"
        f"  기대 {case['expected_verdict']} / 실제 {v.verdict}"
    )
    assert list(v.missing) == case["expected_missing"], (
        f"{case_id}: 미충족 목록이 다르다 (순서 포함)\n"
        f"  기대 {case['expected_missing']} / 실제 {list(v.missing)}"
    )
    assert v.source is not None and v.source.doc_id == case["source"], (
        f"{case_id}: 판정 근거 규정이 다르다 — 화면이 잘못된 규정을 인용하게 된다\n"
        f"  기대 {case['source']} / 실제 {v.source.doc_id if v.source else None}"
    )


@pytest.mark.parametrize("case_id, case", CASES)
def test_차단된_건은_미충족_필드를_반드시_알려준다(case_id, case):
    """`blocked` 인데 `missing` 이 비면 상담원이 무엇을 채워야 할지 알 수 없다 —
    차단만 하고 이유를 숨기면 게이트가 아니라 장애물이다."""
    v = RuleClosureGateAdapter().evaluate(case_id, case["closure_type"], case["evidence"])
    if v.verdict == "blocked":
        assert v.missing, f"{case_id}: 차단인데 미충족 목록이 비었다"
    else:
        assert not v.missing, f"{case_id}: 통과인데 미충족 목록이 있다"
