#!/usr/bin/env python3
# Requirement: E-3
"""실측 STT 쌍 → 오류 프로파일 (w5-stt-error-injector).

입력은 `scripts/measure_bandwidth_penalty.py` 가 남긴 `data/processed/bandwidth-penalty/result.json` —
정답 전사 ↔ Chirp 출력 쌍이다. 원본 조건(16kHz)과 8kHz 조건을 **둘 다** 센다: 같은 발화의 두 번의 STT 라
유형 분포를 보는 데는 표본이 두 배가 되지만, **서로 독립이 아니다**(대부분 같은 오류를 낸다). 그래서 조건별로도 따로 찍는다.

    .venv/bin/python scripts/build_stt_error_profile.py

출력을 `ai/apps/evaluation/error_injection/profile.py` 의 상수로 옮긴다. **원문 텍스트는 옮기지 않는다** —
AI Hub 데이터라 저장소에 싣지 않는다(`ai/CLAUDE.md` §5). 옮기는 것은 건수와 자모 혼동표(낱자)뿐이다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai" / "apps"))

from evaluation.error_injection.classify import TYPES, EditProfile, accumulate  # noqa: E402
from evaluation.metrics.asr import normalize_hypothesis, normalize_reference  # noqa: E402

CONDITIONS = ("original", "8000Hz")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", type=Path, default=ROOT / "data/processed/bandwidth-penalty/result.json")
    args = ap.parse_args()

    data = json.loads(args.result.read_text(encoding="utf-8"))
    profiles = {cond: EditProfile() for cond in (*CONDITIONS, "__all__")}
    for item in data["items"]:
        ref = normalize_reference(item["reference"])
        for cond in CONDITIONS:
            hyp = normalize_hypothesis(item[cond]["transcript"])
            accumulate(profiles[cond], ref, hyp)
            accumulate(profiles["__all__"], ref, hyp)

    print(f"출처 {args.result.relative_to(ROOT)} · 측정일 {data['measured_at']} · 시드 {data['seed']} · 발화 {data['sample_count']}건")
    for cond, p in profiles.items():
        total = sum(p.counts.values())
        print(f"\n[{cond}] 쌍 {p.pairs} · 정답 단어 {p.reference_words} · 편집 구간 {total}")
        for t in TYPES:
            n = p.counts.get(t, 0)
            print(f"  {t:17s} {n:3d}  ({n / total:.1%})" if total else f"  {t:17s} {n:3d}")
    print("\n[__all__] 자모 혼동 (자리, 정답, STT) → 건수")
    for key, n in profiles["__all__"].jamo_confusions.most_common():
        print(f"  {key} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
