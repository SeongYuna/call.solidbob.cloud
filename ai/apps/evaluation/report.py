# Requirement: E-4
"""리포트 출력. [평가 설계 6.2절 원칙 3·4]: 기준선 미달은 CI 실패로 처리하고, 절대
규칙(C-5, F-2) 위반은 평균값 뒤에 숨기지 않고 항상 따로 강조한다.

**잰 것과 못 잰 것을 구분해 찍는다** (2026-08-28). 숫자만 나열하면 "P1~P7 누락 0건"이
실제로는 세 패턴만 보고 낸 값이라는 사실이 사라진다 — 절대 원칙 10.
커버리지는 합성 루트(`scripts/run_eval.py`)가 어댑터 선언과 골든셋을 대조해 넘겨준다.
"""

from __future__ import annotations

from pathlib import Path


def print_report(
    report: dict,
    golden_set_path: Path,
    masking_coverage: dict[str, list[str]] | None = None,
) -> None:
    print(f"골든셋: {golden_set_path}")
    print("=" * 60)
    for section, result in report.items():
        print(f"\n[{section}]")
        if isinstance(result, str):
            print(f"  {result}")
            continue
        for key, value in result.items():
            print(f"  {key}: {value}")
        if section == "masking" and masking_coverage:
            _print_masking_coverage(masking_coverage)
        if result.get("absolute_rule_passed") is False:
            print("  ⛔ 절대 규칙 위반 — 평균으로 통과시키지 않는다 (6.2절 원칙 4)")


def _print_masking_coverage(coverage: dict[str, list[str]]) -> None:
    """C-5 「누락 0건」이 **몇 개 패턴 위에서 나온 값인지** 함께 찍는다.

    `uncovered` 는 어댑터가 지원한다고 선언했는데 **골든셋에 표본이 없는** 패턴이다.
    그 패턴에 대해서는 절대 규칙이 통과한 것이 아니라 **판정된 적이 없다.**
    `rule_fallback` 은 명세(2.4절 NER)와 **다른 방식**으로 잡는 패턴이다 — 장민석이
    2026-08-27 에 어댑터의 `PARTIAL_PATTERNS` 로 선언해 뒀고, 여기가 그 목적지다.
    """
    measured = coverage.get("measured") or []
    uncovered = coverage.get("uncovered") or []
    fallback = coverage.get("rule_fallback") or []
    print(f"  측정한 패턴: {', '.join(measured) if measured else '없음'}")
    if fallback:
        print(f"  규칙 폴백(명세는 NER): {', '.join(fallback)}")
    if uncovered:
        print(f"  ⚠ 표본 없는 패턴: {', '.join(uncovered)} — 이 패턴은 판정된 적이 없다")
        print("     「누락 0건」은 위 '측정한 패턴' 범위 안에서만 성립한다 (절대 원칙 10)")
