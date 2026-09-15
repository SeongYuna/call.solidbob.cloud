#!/usr/bin/env python3
# Requirement: C-1, C-2, C-3, C-4
"""C-1~C-4 규칙을 **실제 다산콜센터 상담원 답변**(AI Hub 민원 질의응답, validation)에 돌려 무엇이 걸리는지 센다.

골든셋 값(재현율·정밀도)은 규칙을 **골든셋을 본 뒤에** 썼으므로 상한이다. 여기는 규칙 작성자가 보지 않은 발화다.
⚠ **라벨이 없다** — 걸린 것이 진짜 위반인지 아닌지 이 스크립트는 판정하지 않는다. 건수와 문장을 찍고, 판정은 사람이 한다.
원천 데이터는 저장소에 없다(`data/raw/`, gitignore). 출력에 문장이 나오므로 결과를 커밋하지 않는다(개인정보는 AI Hub 가 비식별 처리한 데이터다).

    .venv/bin/python scripts/measure_compliance_real_agents.py --split dev    # 규칙을 고칠 때 보는 절반
    .venv/bin/python scripts/measure_compliance_real_agents.py --split test   # 보고하는 절반 — 이걸 보고 규칙을 고치지 않는다

**개발/보류를 가른다.** 같은 발화로 규칙을 고치고 같은 발화로 과탐지를 보고하면 또 자기충족이다. 대화셋 일련번호의
숫자 끝자리 홀짝으로 가른다(한 대화의 발화가 양쪽에 섞이지 않는다). 2026-09-15 첫 실행은 가르기 전 전체였다 — 그 값은 기록에 남긴다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps")]

from compliance.domain.services.detector import detect  # noqa: E402


def _split_of(dialog_id: str) -> str:
    digits = "".join(ch for ch in dialog_id if ch.isdigit())
    return "dev" if digits and int(digits[-1]) % 2 == 0 else "test"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    args = ap.parse_args()
    files = sorted((ROOT / "data" / "raw" / "aihub-minwon-qa" / "validation" / "label" / "다산콜센터").glob("*.json"))
    utterances = []
    for f in files:
        for row in json.loads(f.read_text(encoding="utf-8")):
            if row.get("화자") == "상담사" and (args.split == "all" or _split_of(row.get("대화셋일련번호", "")) == args.split):
                text = (row.get("상담사답변") or row.get("상담사질문(요청)") or "").strip()
                if text:
                    utterances.append((f.stem.split("_")[-2], text))
    flagged = [(cat, t, detect(t)) for cat, t in utterances]
    flagged = [x for x in flagged if x[2]]
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"측정일 {date.today()} · 커밋 {head}-dirty · AI Hub 민원 질의응답 validation 다산콜센터 {len(files)}파일 · 절반 {args.split} · 상담사 발화 {len(utterances)}건")
    print(f"걸린 발화 {len(flagged)}건 ({len(flagged) / len(utterances):.2%}) · 코드별 {dict(Counter(d.code for _, _, ds in flagged for d in ds))}")
    for cat, t, ds in flagged:
        print(f"  [{cat}] {[f'{d.code}:{d.phrase}' for d in ds]}  ← {t[:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
