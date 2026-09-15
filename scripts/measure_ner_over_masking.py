#!/usr/bin/env python3
# Requirement: C-5
"""C-5 NER 과잉 마스킹 — **개인정보가 없는 골든셋 발화**에서 NER 이 무엇을 더 가리는지 센다.

하네스의 `over_masking_rate` 는 음성 케이스(`masked_expected: false`)만 분모로 쓴다 — v1-150 에서 4건이다.
그 4건에서 0.0 이 나와도 «NER 이 멀쩡한 자막을 지우지 않는다» 는 말은 못 한다. 그래서
`pii_patterns` 가 **비어 있는** 발화 전부에 규칙·NER 두 겹을 돌려 **NER 이 새로 가린 구간**을 뽑는다.

⚠ 여기서 나온 구간이 전부 오탐은 아니다 — 골든셋이 라벨을 안 단 실제 이름·주소일 수 있다.
그래서 비율 하나로 내지 않고 **가린 조각을 그대로 찍는다.** 판정은 사람이 목록을 보고 한다.
출력에 원문 조각이 나오지만 골든셋은 팀이 지어낸 문장(`source: authored`)이거나 공개 데이터다.

    .venv/bin/python scripts/measure_ner_over_masking.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]

from evaluation.golden_set import load_golden_set  # noqa: E402
from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter  # noqa: E402
from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger  # noqa: E402
from pii_ner.adapter.outbound.layered_masking_adapter import LayeredMaskingAdapter  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden-set", type=Path, default=ROOT / "golden-set" / "v1-150.json")
    ap.add_argument("--ner-model", type=Path, default=ROOT / "models" / "koelectra-ner")
    args = ap.parse_args()

    items = load_golden_set(args.golden_set)
    rule = RuleMaskingAdapter()
    layered = LayeredMaskingAdapter(rule, KoElectraNerTagger(args.ner_model))

    texts = []
    for it in items:
        if it.pii_patterns:
            continue
        for who, text in (("customer", it.customer_utterance), ("agent", getattr(it, "agent_utterance", None))):
            if text:
                texts.append((it.id, who, text))

    added = []
    for item_id, who, text in texts:
        _, rule_spans = rule.mask(text)
        _, spans = layered.mask(text)
        rule_ranges = {s.span for s in rule_spans}
        for s in spans:
            if s.span not in rule_ranges and s.type in ("P6", "P7"):
                added.append((item_id, who, s.type, text[s.span[0]:s.span[1]], text))

    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                           capture_output=True, text=True).stdout.strip()
    print(f"측정일 {date.today()} · 커밋 {commit}{'-dirty' if dirty else ''} · 골든셋 {args.golden_set.name} · 모델 {args.ner_model.name}")
    print(f"개인정보 라벨 없는 발화 {len(texts)}건 중 NER 이 새로 가린 발화 "
          f"{len({(a[0], a[1]) for a in added})}건 · 구간 {len(added)}개")
    for item_id, who, pattern, piece, text in added:
        print(f"  {item_id} {who:8} {pattern} 「{piece}」  ← {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
