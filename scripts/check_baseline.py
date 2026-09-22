# Requirement: E-4, QUA-2
"""기준선 게이트 — 하네스 리포트(JSON)가 기준선 아래면 실패한다 (`w2-baseline-gate`, 절대 원칙 5).

    python scripts/run_eval.py --runs 3 --report-json /tmp/report.json --no-ner --retriever bm25
    python scripts/check_baseline.py /tmp/report.json            # 기준선 아래면 exit 1

기준선은 **측정한 값**이다 — 기획서 목표치가 아니라 `_project/STATE.md` 「실측값」의 운영 구성
(규칙 + BM25, run_id 4 · 커밋 `e966b62` · 골든셋 v1-150.1 · 3회 최저)을 그대로 옮겼다.
숫자를 여기서 손으로 올리지 않는다 — 재측정 뒤 `run_id` 와 함께 바꾼다(§5).

세 갈래로 보고한다(절대 원칙 5 「통과는 잰 범위 안에서만」):
  FAIL      값이 있는데 기준선 아래 — exit 1
  PASS      값이 있고 기준선 이상
  NO_SAMPLES / NOT_IMPLEMENTED  표본이 없거나 모듈이 없다 — 통과도 실패도 아니다. 경고만 낸다

절대 규칙(C-5 누락 · F-2 판정)은 평균이 아니라 **1건이라도 뚫리면 FAIL** 이다.
⚠ CI(`test.yml` `ai` job)에는 아직 붙이지 않았다 — 러너에 Elasticsearch 도 지식베이스 색인도 없어
검색 항목이 전부 「측정 불가」로 나온다. 붙이려면 ES 서비스 + `index_knowledge_base.py --to-es` 단계가 먼저다.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# 운영 구성(규칙 + BM25) 실측 최저치 — run_id 4, 2026-09-22, 커밋 e966b62, 골든셋 v1-150.1 (n 96 / 28 / 99)
BASELINE: dict[str, dict[str, float]] = {
    "retrieval": {"recall_at_k": 0.812, "mrr": 0.635},
}
# 절대 규칙 — 1건이라도 뚫리면 실패
ABSOLUTE: dict[str, str] = {
    "masking": "absolute_rule_passed",
    "closure_gate": "absolute_rule_passed",
}


def _is_unmeasured(value) -> bool:
    return not isinstance(value, dict)  # 하네스는 측정 불가를 문자열(NO_SAMPLES / NOT_IMPLEMENTED)로 넣는다


def check(report: dict) -> tuple[list[str], list[str], list[str]]:
    fails: list[str] = []
    passes: list[str] = []
    unmeasured: list[str] = []

    for section, floors in BASELINE.items():
        block = report.get(section)
        if _is_unmeasured(block):
            unmeasured.append(f"{section}: {block}")
            continue
        for metric, floor in floors.items():
            value = block.get(metric)
            if value is None or (isinstance(value, float) and math.isnan(value)):
                unmeasured.append(f"{section}.{metric}: 값 없음")
                continue
            line = f"{section}.{metric} = {value:.3f} (기준선 {floor:.3f}, n {block.get('n', '?')})"
            (passes if value >= floor else fails).append(line)

    for section, flag in ABSOLUTE.items():
        block = report.get(section)
        if _is_unmeasured(block):
            unmeasured.append(f"{section}: {block}")
            continue
        passed = block.get(flag)
        detail = block.get("missed_items") or block.get("failed_items") or []
        line = f"{section}.{flag} = {passed} (뚫린 건 {len(detail)}: {', '.join(map(str, detail[:5]))})"
        (passes if passed is True else fails).append(line)

    return fails, passes, unmeasured


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    report = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    fails, passes, unmeasured = check(report)
    for line in passes:
        print(f"PASS  {line}")
    for line in unmeasured:
        print(f"WARN  측정 불가 — {line}")
    for line in fails:
        print(f"FAIL  {line}", file=sys.stderr)
    if fails:
        print(f"\n기준선 미달 {len(fails)}건 — CI 실패(절대 원칙 5).", file=sys.stderr)
        return 1
    print(f"\n기준선 통과 {len(passes)}건 · 측정 불가 {len(unmeasured)}건(통과 아님).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
