#!/usr/bin/env python3
# Requirement: A-5, COST-1
"""8kHz 협대역이 STT 정확도를 얼마나 깎는지 잰다 — 같은 음성을 원본과 8kHz 로 각각 전사한다.

## 왜 이것부터 재는가

`w3-a5-translation-spike` 의 완료 조건 넷째가 *"같은 표본을 원본으로도 재서 8kHz 가 얼마나
깎아먹는지 분리했다"* 이다. A-5 평가에 쓸 외국인 화자 데이터(AI Hub 505·71479)는 **아직
없지만**, 그 실험의 **교란 요인 하나는 지금 가진 데이터로 분리할 수 있다.**

이게 중요한 이유: 외국인 화자 데이터가 도착해 WER 이 나쁘게 나왔을 때, 그것이
**「어눌한 한국어라서」인지 「8kHz 로 낮춰서」인지** 구분할 방법이 없으면 A-5 를 코어에서
뺄지 말지 판단할 수 없다. 이 스크립트가 그 **기준선(내국인·같은 파이프라인)**을 만든다.

## 무엇을 쓰는가

`data/raw/aihub-krespspeech/` — AI Hub 「고객 응대 음성」, **16kHz** 모노, 정답 전사 동봉.
우리 실제 통화는 **8kHz 협대역**이다(다산콜DB 8000Hz · 저품질전화 8000Hz).
`ffmpeg` 으로 8kHz 로 낮춘 사본을 만들어 **같은 발화를 두 조건으로** 전사한다.

⚠ **이 수치는 다운샘플링의 영향만 분리한 것이다.** 실제 전화망은 다운샘플링뿐 아니라
코덱 압축·잡음·라인 손실이 함께 걸리므로 **여기서 나온 값보다 나쁘다.** 그대로
「8kHz 페널티」라고 옮겨 적으면 절대 원칙 10 위반이다.

## 비용 (COST-1)

`scripts/transcribe_batch.py` 의 예산 가드를 그대로 쓴다 — `data/processed/stt-usage.json`
에 누적하고 `.env` 의 `STT_MAX_SECONDS_PER_DAY`/`_MONTH` 를 넘기면 **요청을 보내지 않는다.**
한 표본이 **두 번**(원본·8kHz) 전사되므로 실제 소모는 오디오 길이의 2배다.

    python3 scripts/measure_bandwidth_penalty.py --limit 20 --dry-run   # 쓸 초만 계산
    python3 scripts/measure_bandwidth_penalty.py --limit 20
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import shutil
import subprocess
import sys
import wave
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO_ROOT / "ai" / "apps"), str(REPO_ROOT / "scripts")]

from evaluation.metrics.asr import (  # noqa: E402
    NORMALIZATION_RULES,
    aggregate_by_group,
)
from transcribe_batch import (  # noqa: E402
    Budget,
    audio_meta,
    load_env,
    transcribe,
)

SOURCE_ROOT = REPO_ROOT / "data" / "raw" / "aihub-krespspeech" / "validation"
WORK_DIR = REPO_ROOT / "data" / "processed" / "bandwidth-penalty"
TARGET_RATE = 8000  # 전화망 표준. 다산콜DB·저품질전화 실측이 전부 8000Hz 다


def pick_samples(limit: int, seed: int) -> list[tuple[Path, Path]]:
    """(wav, label) 짝을 뽑는다. **시드를 고정한다** — 표본이 바뀌면 재측정 비교가 안 된다."""
    labels = sorted((SOURCE_ROOT / "label").rglob("*.txt"))
    if not labels:
        raise SystemExit(f"라벨이 없다: {SOURCE_ROOT / 'label'}  (data/README.md 참고)")

    pairs = []
    for label in labels:
        wav = SOURCE_ROOT / "wav" / label.relative_to(SOURCE_ROOT / "label").with_suffix(".wav")
        if wav.exists():
            pairs.append((wav, label))
    random.Random(seed).shuffle(pairs)
    return pairs[:limit]


def narrow_path(src: Path) -> Path:
    """8kHz 사본을 둘 경로. **경로 전체로 이름을 만든다.**

    ⚠ 2026-09-09 여기서 한 번 틀렸다. `WORK_DIR / "8k" / src.name` 을 썼는데
    **AI Hub 파일이 전부 `0001.wav`** 다(세션 폴더로 구분된다). 20건이 같은 파일에 덮여
    쓰였고 `if dst.exists()` 캐시가 첫 번째 것을 계속 돌려줘서, **8kHz 전사 20건이 전부
    같은 문장**이 됐다. 결과는 WER 1.115 — 「8kHz 가 이만큼 나쁘다」로 읽힐 뻔했다.
    측정 도구의 버그가 측정 대상의 성질로 보이는 전형적인 모양이다.
    """
    rel = src.relative_to(SOURCE_ROOT / "wav")
    return WORK_DIR / "8k" / "_".join(rel.parts)


def downsample(src: Path, dst: Path) -> Path:
    """ffmpeg 으로 8kHz 모노 LINEAR16 사본을 만든다. 이미 있으면 다시 만들지 않는다."""
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src),
         "-ar", str(TARGET_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
        check=True,
    )
    return dst


def duration_seconds(path: Path) -> float:
    with contextlib_closing(wave.open(str(path), "rb")) as w:
        return w.getnframes() / float(w.getframerate())


def contextlib_closing(thing):
    import contextlib
    return contextlib.closing(thing)


def main() -> int:
    ap = argparse.ArgumentParser(description="8kHz 다운샘플링이 STT 를 얼마나 깎는지 잰다")
    ap.add_argument("--limit", type=int, default=20, help="표본 수 (한 건당 전사 2회)")
    ap.add_argument("--seed", type=int, default=20260909, help="표본 추출 시드 — 재측정 때 같게 둔다")
    ap.add_argument("--dry-run", action="store_true", help="쓸 초만 계산하고 요청을 보내지 않는다")
    ap.add_argument("--out", type=Path, default=WORK_DIR / "result.json")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg 이 없다 —  brew install ffmpeg")

    env = load_env(REPO_ROOT / ".env")
    os.environ.update({k: v for k, v in env.items() if k not in os.environ})

    samples = pick_samples(args.limit, args.seed)
    if not samples:
        raise SystemExit("짝이 맞는 (wav, label) 이 하나도 없다")

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    total_seconds = sum(duration_seconds(wav) for wav, _ in samples) * 2  # 원본 + 8kHz
    print(f"표본 {len(samples)}건 · 전사 {len(samples) * 2}회 · 오디오 {total_seconds:.0f}초")

    budget = Budget(int(env.get("STT_MAX_SECONDS_PER_DAY") or 0),
                    int(env.get("STT_MAX_SECONDS_PER_MONTH") or 0))
    allowed, why = budget.allows(total_seconds)
    print(f"예산 — 오늘 {budget.used_today:.0f}초 사용 · 이번 달 {budget.used_month:.0f}초 사용")
    if not allowed:
        raise SystemExit(f"COST-1 가드에 걸렸다: {why}")
    if args.dry_run:
        print("--dry-run — 요청을 보내지 않았다")
        return 0

    from google.cloud import speech  # noqa: PLC0415
    client = speech.SpeechClient()

    rows: list[tuple[str, str, str]] = []
    per_item: list[dict] = []
    for i, (wav, label) in enumerate(samples, start=1):
        reference = label.read_text(encoding="utf-8").strip()
        narrow = downsample(wav, narrow_path(wav))

        item = {"wav": str(wav.relative_to(REPO_ROOT)), "reference": reference}
        for condition, path in (("original", wav), (f"{TARGET_RATE}Hz", narrow)):
            meta = audio_meta(path)
            result = transcribe(client, speech, path, meta)
            budget.charge(meta.seconds)
            hypothesis = result["transcript"]
            rows.append((condition, reference, hypothesis))
            item[condition] = {"rate": meta.rate, "transcript": hypothesis}
        per_item.append(item)
        print(f"  [{i}/{len(samples)}] {wav.relative_to(SOURCE_ROOT / 'wav')}")

    scores = aggregate_by_group(rows)

    print("\n" + "=" * 60)
    print("8kHz 협대역 페널티 — 같은 발화, 두 조건")
    print("=" * 60)
    for condition in sorted(k for k in scores if k != "__all__"):
        s = scores[condition]
        print(f"  {condition:>10}   WER {s['wer']:.3f} · CER {s['cer']:.3f} · n {s['n']}")
    orig, narrow_s = scores.get("original"), scores.get(f"{TARGET_RATE}Hz")
    if orig and narrow_s and orig["n"] and narrow_s["n"]:
        print(f"\n  차이       WER +{narrow_s['wer'] - orig['wer']:.3f} "
              f"· CER +{narrow_s['cer'] - orig['cer']:.3f}")

    print("\n적용한 정규화:")
    for rule in NORMALIZATION_RULES:
        print(f"  - {rule}")
    print("\n⚠ 이 값은 **다운샘플링의 영향만** 분리한 것이다. 실제 전화망에는 코덱 압축·잡음·")
    print("  라인 손실이 더해지므로 여기서 나온 값보다 나쁘다. 그대로 옮겨 적지 않는다.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "measured_at": dt.date.today().isoformat(),
        "dataset": "aihub-krespspeech/validation",
        "seed": args.seed,
        "sample_count": len(samples),
        "audio_seconds": round(total_seconds, 1),
        "normalization": list(NORMALIZATION_RULES),
        "scores": scores,
        "items": per_item,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과: {args.out.relative_to(REPO_ROOT)}  (전사 원문 포함 — .gitignore 대상)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
