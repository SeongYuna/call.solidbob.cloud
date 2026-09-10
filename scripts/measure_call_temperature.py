#!/usr/bin/env python3
# Requirement: D-5
"""통화 온도 가설 검증 — **상담사의 톤은 일정하고 민원인의 톤은 흔들리는가.**

`_project/decisions/203`. 검토에서 권고받은 방법(가설을 자연어 단계로 쪼갠 뒤 그 단계를
수행할 기술을 찾는다)을 그대로 따른다.

```
가설 1  상담사의 톤은 통화 내내 일정하다        → 화자별 F0·에너지 분산을 잰다
가설 2  민원인의 톤은 상담사보다 넓게 흔들린다   → 두 화자의 분산을 비교한다
가설 3  흔들리는 구간은 국소적이다              → 로버스트 z 로 이상 구간을 센다
가설 4  그 구간이 상담 품질과 관련이 있다        → ⚠ 못 잰다. 품질 라벨이 없다
```

**가설 1·2·3 은 오늘 잴 수 있다.** 서울 열린데이터광장 다산콜DB 가 파일명에 화자 역할을
담고 있다 — `<시나리오>_<연령대>_<성별>_<지역>_<민원인|상담사>_<take>.wav`.
민원인 5,549건 · 상담사 1,044건.

⚠ **연기된 시나리오 음성이다.** 실제 민원 통화가 아니므로 여기서 나온 분산 차이가
실통화에서도 같은지는 확인할 수 없다. 그대로 「실측」이라고 옮겨 적지 않는다(절대 원칙 10).

⚠ **8kHz 협대역이라 F0 추정에 옥타브 오류가 섞인다.** 그래서 절대값을 비교하지 않고
**같은 화자 역할 안에서의 분산**을 본다. `voiced_ratio` 가 낮은 발화는 제외한다.

    python3 scripts/measure_call_temperature.py --per-role 150
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO_ROOT / "ai" / "apps")]

import numpy as np  # noqa: E402

from voice_signal.adapter.outbound.wav_reader import read_mono  # noqa: E402
from voice_signal.domain.services.features import extract  # noqa: E402
from voice_signal.domain.services.outlier import summarize_speaker  # noqa: E402

AUDIO_ROOT = REPO_ROOT / "data" / "raw" / "seoul-minwon-audio" / "민원상담_음성" / "다산콜DB"
OUT = REPO_ROOT / "data" / "processed" / "call-temperature" / "hypothesis.json"

# `1_10~50대_남성_서울_민원인_3.wav` · `1_남성_상담사_2.wav`
# 필드 수가 역할마다 달라서 위치가 아니라 **이름으로** 찾는다.
_ROLE = re.compile(r"(민원인|상담사)")
_SCENARIO = re.compile(r"^(\d+)_")


def collect(per_role: int, seed: int) -> dict[str, list[Path]]:
    files = sorted(AUDIO_ROOT.glob("*.wav"))
    if not files:
        raise SystemExit(f"음성이 없다: {AUDIO_ROOT}  (data/README.md 참고)")
    by_role: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        m = _ROLE.search(f.name)
        if m:
            by_role[m.group(1)].append(f)
    rng = random.Random(seed)
    return {role: rng.sample(paths, min(per_role, len(paths)))
            for role, paths in sorted(by_role.items())}


def scenario_of(path: Path) -> str:
    m = _SCENARIO.match(path.name)
    return m.group(1) if m else "?"


def main() -> int:
    ap = argparse.ArgumentParser(description="상담사 vs 민원인 톤 분산 비교")
    ap.add_argument("--per-role", type=int, default=150, help="역할당 표본 수")
    ap.add_argument("--seed", type=int, default=20260909)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    samples = collect(args.per_role, args.seed)
    print(f"표본 — " + " · ".join(f"{r} {len(p)}건" for r, p in samples.items()))

    rows: dict[str, list[dict]] = {}
    for role, paths in samples.items():
        feats = []
        for p in paths:
            audio, rate = read_mono(p)
            f = extract(audio, rate)
            feats.append({
                "file": p.name,
                "scenario": scenario_of(p),
                "duration_s": round(f.duration_s, 2),
                "voiced_ratio": round(f.voiced_ratio, 3),
                "f0_median_hz": None if np.isnan(f.f0_median_hz) else round(f.f0_median_hz, 1),
                "f0_spread_hz": None if np.isnan(f.f0_spread_hz) else round(f.f0_spread_hz, 1),
                "energy_median_db": round(f.energy_median_db, 2),
                "energy_spread_db": round(f.energy_spread_db, 2),
                "reliable": f.is_reliable,
            })
        rows[role] = feats
        print(f"  {role} — 특징 추출 완료 ({len(feats)}건)")

    print("\n" + "=" * 68)
    print("가설 1·2 — 화자 역할별 톤 분산  (신뢰 가능한 발화만)")
    print("=" * 68)
    summary: dict[str, dict] = {}
    for role, feats in rows.items():
        ok = [f for f in feats if f["reliable"] and f["f0_median_hz"] is not None]
        f0 = [f["f0_median_hz"] for f in ok]
        db = [f["energy_median_db"] for f in ok]
        dur = [f["duration_s"] for f in ok]
        if len(f0) < 4:
            print(f"  {role}: 신뢰 가능한 표본 {len(f0)}건 — 측정 불가")
            summary[role] = {"n": len(f0), "status": "측정 불가 — 표본 부족"}
            continue

        # 화자 개인차를 걷어내려면 **역할 안의 분산**을 봐야 하는데, 발화가 다른 사람들
        # 것이라 개인차가 섞인다. 그래서 두 가지를 함께 낸다 —
        #   ① 역할 전체의 F0 분포 폭(개인차 포함)
        #   ② **발화 하나 안에서의** F0 흔들림(f0_spread) 의 중앙값 — 개인차가 안 섞인다
        # 가설 1·2 가 말하는 「톤이 일정하다」는 ② 쪽이다.
        within = [f["f0_spread_hz"] for f in ok if f["f0_spread_hz"] is not None]
        summary[role] = {
            "n": len(f0),
            "f0_median_hz": round(statistics.median(f0), 1),
            "f0_iqr_hz": round(np.percentile(f0, 75) - np.percentile(f0, 25), 1),
            "within_utterance_f0_spread_median_hz": round(statistics.median(within), 1) if within else None,
            "energy_median_db": round(statistics.median(db), 2),
            "energy_iqr_db": round(np.percentile(db, 75) - np.percentile(db, 25), 2),
            "duration_median_s": round(statistics.median(dur), 2),
            "voiced_ratio_median": round(statistics.median([f["voiced_ratio"] for f in ok]), 3),
        }
        s = summary[role]
        print(f"  {role}  n={s['n']}")
        print(f"     발화 안 F0 흔들림(중앙값)  {s['within_utterance_f0_spread_median_hz']} Hz   ← 가설 1·2 의 축")
        print(f"     역할 전체 F0 중앙값/IQR    {s['f0_median_hz']} / {s['f0_iqr_hz']} Hz  (개인차 포함)")
        print(f"     에너지 중앙값/IQR          {s['energy_median_db']} / {s['energy_iqr_db']} dB")
        print(f"     발화 길이 중앙값           {s['duration_median_s']} s")

    a, b = summary.get("상담사"), summary.get("민원인")
    verdict = None
    if a and b and a.get("within_utterance_f0_spread_median_hz") and b.get("within_utterance_f0_spread_median_hz"):
        ratio = b["within_utterance_f0_spread_median_hz"] / a["within_utterance_f0_spread_median_hz"]
        verdict = round(ratio, 3)
        print(f"\n  민원인 / 상담사 발화 내 F0 흔들림 비 = {ratio:.2f}")
        print("  > 1 이면 가설 2 방향(민원인이 더 흔들린다). 1 근처면 **차이를 검출하지 못한 것**이다.")

    # 가설 3 — 시나리오를 「통화」로 보고 화자별 이상 구간을 센다.
    print("\n" + "=" * 68)
    print("가설 3 — 시나리오(=통화) 안에서 이상 구간이 잡히는가")
    print("=" * 68)
    temp_rows = []
    for role, feats in rows.items():
        by_scenario: dict[str, list[float]] = defaultdict(list)
        for f in feats:
            if f["reliable"] and f["f0_median_hz"] is not None:
                by_scenario[f["scenario"]].append(f["f0_median_hz"])
        usable = 0
        outliers = 0
        for scenario, values in by_scenario.items():
            t = summarize_speaker(f"{role}/{scenario}", values)
            if t.baseline_usable:
                usable += 1
                outliers += t.outlier_count
                temp_rows.append({"role": role, "scenario": scenario,
                                  "n": t.utterance_count, "mad_hz": round(t.spread, 2),
                                  "outliers": t.outlier_count})
        print(f"  {role}: 기준선을 세울 수 있는 시나리오 {usable}개 · 이상 구간 {outliers}건")
        if usable == 0:
            print(f"     └ 시나리오당 발화가 8건 미만이라 판정하지 않았다 "
                  f"(「이상 없음」이 아니라 「재지 않았다」)")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "measured_at": dt.date.today().isoformat(),
        "dataset": "seoul-minwon-audio/다산콜DB (연기된 시나리오 음성 — 실통화 아님)",
        "seed": args.seed,
        "per_role": args.per_role,
        "summary": summary,
        "within_utterance_spread_ratio_민원인_over_상담사": verdict,
        "scenario_baselines": temp_rows,
        "caveats": [
            "연기된 시나리오 음성이라 실제 민원 통화와 다를 수 있다",
            "8kHz 협대역이라 F0 추정에 옥타브 오류가 섞인다",
            "역할 전체 F0 분포에는 화자 개인차가 섞여 있다 — 가설의 축은 발화 내 흔들림 쪽이다",
            "상담 품질 라벨이 없어 가설 4(품질과의 관련)는 측정 불가",
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과: {args.out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
