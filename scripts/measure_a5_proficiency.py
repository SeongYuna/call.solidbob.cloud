#!/usr/bin/env python3
# Requirement: A-5, COST-1
"""외국인 화자의 어눌한 한국어를 상용 STT 가 얼마나 알아듣는지 — **숙련도 등급별 WER/CER**.

## 무엇을 재는가

`w3-a5-translation-spike` 의 본체다. AI Hub 71479(외국인 한국어 발화, 숙련도 4등급 라벨)
Validation 에서 등급별로 표본을 층화 추출해 **8 kHz 로 낮춘 뒤** Google STT 로 전사하고,
정답 전사(`RecordingMetadata.orthographic`)와 대조해 WER/CER 을 **등급별로 따로** 낸다
(`aggregate_by_group` — 전체 평균 하나로 뭉개지 않는다).

같은 표본의 일부는 **원본(48 kHz)으로도** 전사해 「어눌한 한국어라서」와 「8 kHz 로 낮춰서」의
몫을 분리한다(09-09 `measure_bandwidth_penalty.py` 와 같은 설계).

## ⚠ 이 수치는 상한이다 — 리포트 옆에 반드시 붙는다

① 온라인 녹음(48 kHz, 잡음 없음)을 **다운샘플만** 했다. 실제 전화망의 코덱·잡음·라인 손실은
   없다 → 실제 통화에서는 더 나쁘다.
② 과제가 질문답변(ATQ)·낭독(LAR)이라 **민원 어휘가 아니다.**
③ STT 예산 때문에 **3~6초 짧은 발화만** 골랐다(중앙값 7.5초). 긴 발화는 다르게 나올 수 있다.
④ 모어 분포가 인도네시아·베트남에 편중돼 있다(데이터셋 자체가 그렇다).
⑤ 등급당 n=20 — 등급 간 차이가 표본 잡음보다 작을 수 있다.

목표치를 지어내지 않는다. 결과가 나쁘면 나쁜 대로 적는다(절대 원칙 2·8·10).

## 비용 (COST-1)

`scripts/transcribe_batch.py` 의 예산 가드·장부(`data/processed/stt-usage.json`)를 **그대로**
쓴다. 가드가 거부하면 요청을 보내지 않고 멈춘다 — 우회하지 않는다. 표본 설계로 예산을
맞춘다: 등급 4 × 20건 × 3~6초 ≈ 360초 + 원본 재측정 등급당 5건 ≈ 90초. `--max-total-sec`
(기본 550) 을 넘으면 실측 전에 멈추고 건수를 줄이라고 말한다.

    .venv/bin/python scripts/measure_a5_proficiency.py --dry-run   # 표본·총 초만. STT 안 부른다
    .venv/bin/python scripts/measure_a5_proficiency.py             # v1 기본 모델(09-21 첫 실측)
    .venv/bin/python scripts/measure_a5_proficiency.py --stt-model chirp_3 --region us-central1 \
        --original-subset 0 --probe                                 # v2 Chirp 3 — 1건만 불러 응답 확인
    .venv/bin/python scripts/measure_a5_proficiency.py --stt-model chirp_3 --region us-central1 --original-subset 0

## 모델 (2026-09-21 추가)

`--stt-model` 은 `v1`(기본 — 첫 실측이 그대로 재현된다) · `chirp_3` · `chirp_2`(v2 지역 엔드포인트,
`transcribe_batch.transcribe_v2`). **표본은 시드로 고정돼 모델만 바뀐다** — 같은 80건을 다른 모델로
재는 것이라 직접 비교가 된다. 전사 캐시 키에 모델 이름이 붙어(`cache_key`) v1 캐시와 섞이지 않고,
결과 파일도 `-chirp3` 접미가 붙는다(`output_paths`).

## 데이터 (gitignore)

`data/raw/aihub-foreign-proficiency-71479/validation/` —
`label/VL_Speech_lab/*.json`(22,447) · `wav/VS_Speech_sound.zip`(20 GB, **풀지 않는다**).
표본만 `unzip <zip> "/<이름>.wav"` 로 꺼낸다 — zip 항목 이름이 `/` 로 시작한다(unzip 이 떼어 낸다).
라벨↔wav 는 파일명(확장자 제외)으로 짝이 맞는다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO_ROOT / "ai" / "apps"), str(REPO_ROOT / "scripts")]

from evaluation.metrics.asr import (  # noqa: E402
    NORMALIZATION_RULES,
    _edit_distance,
    aggregate_by_group,
)
from transcribe_batch import (  # noqa: E402
    V2_DEFAULT_REGION,
    V2_MODELS,
    Budget,
    audio_meta,
    file_key,
    load_env,
    speech_v2_client,
    transcribe,
    transcribe_v2,
)

STT_MODELS = ("v1",) + V2_MODELS   # v1 = Cloud Speech v1 recognize 기본 모델. 나머지는 v2 지역 엔드포인트

DATASET = "aihub-foreign-proficiency-71479/validation"
SOURCE_ROOT = REPO_ROOT / "data" / "raw" / "aihub-foreign-proficiency-71479" / "validation"
LABEL_DIR = SOURCE_ROOT / "label" / "VL_Speech_lab"
WAV_ZIP = SOURCE_ROOT / "wav" / "VS_Speech_sound.zip"
WORK_DIR = REPO_ROOT / "data" / "processed" / "a5"
PUBLIC_DIR = REPO_ROOT / "jekyll" / "assets"
TARGET_RATE = 8000  # 전화망 표준. 다산콜DB·저품질전화 실측이 전부 8000Hz 다

# 데이터셋의 등급 순서. aggregate_by_group 은 알파벳순으로 돌려주므로 표는 이 순서로 다시 찍는다.
LEVELS = ("Beginner", "Intermediate", "Advance", "Fluent")

# 71479 라벨에만 있는 표기 — AI Hub 505 계열(`(철자)/(발음)` · `n/`)과 규약이 다르다.
# 22,447건 전수 조사(2026-09-21): 문장부호 `.` `?` `,` 가 대부분이고, 그 밖에 제어 문자
# `\x08`(2건) · 굽은따옴표 `‘’“”`(각 1건) · `>`(1건, 오타) · `%`(9건) 이 있다.
# `%` 와 숫자 표기(`십오년` vs `15년`)는 **정규화하지 않는다** — 숫자를 어느 쪽으로 맞추든
# 점수가 움직이므로, 대신 리포트에 그 사실을 적는다.
EXTRA_NORMALIZATION_RULES = (
    "제어 문자(U+0000~U+001F, U+007F) 제거 — 라벨에 `\\x08` 이 섞여 있다",
    "굽은따옴표 `‘’“”` 를 공백으로 — 기본 규칙이 곧은따옴표만 지운다",
)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_CURLY_QUOTES = re.compile(r"[‘’“”]")


def normalize_71479(text: str) -> str:
    """71479 라벨 고유 표기만 정리한다. 나머지(문장부호·NFC·공백)는 `asr.normalize_reference` 가 한다."""
    text = unicodedata.normalize("NFC", text or "")
    text = _CONTROL.sub("", text)
    return _CURLY_QUOTES.sub(" ", text)


@dataclass(frozen=True)
class Sample:
    name: str            # 파일명(확장자 제외) — 라벨과 wav 가 이 이름으로 짝이 맞는다
    user_id: str
    level: str           # SpeakerMetadata.proficiency
    language: str        # 모어
    task: str            # 과제 코드 앞 3글자 (ATQ·LAR·…)
    seconds: float       # RecordedTime — 표본 설계용. 예산은 wav 헤더로 다시 잰다
    reference: str


def parse_label(name: str, data: dict) -> Sample:
    meta, rec = data["SpeakerMetadata"], data["RecordingMetadata"]
    parts = name.split("-")
    task = parts[5][:3] if len(parts) >= 7 else "?"
    return Sample(
        name=name,
        user_id=str(data.get("UserID") or parts[0]),
        level=meta["proficiency"],
        language=meta.get("language", "?"),
        task=task,
        seconds=float(rec["RecordedTime"]),
        reference=rec["orthographic"],
    )


def load_labels(label_dir: Path = LABEL_DIR) -> list[Sample]:
    files = sorted(label_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"라벨이 없다: {label_dir}  (data/README.md 참고)")
    return [parse_label(f.stem, json.loads(f.read_text(encoding="utf-8"))) for f in files]


def stratified_sample(
    samples: list[Sample],
    *,
    per_level: int,
    seed: int,
    min_sec: float,
    max_sec: float,
    max_per_speaker: int = 2,
    levels: tuple[str, ...] = LEVELS,
) -> dict[str, list[Sample]]:
    """등급별 층화 추출. **시드를 고정한다** — 표본이 바뀌면 재측정 비교가 안 된다.

    - 길이 창 `[min_sec, max_sec]` 안의 발화만 후보다(STT 예산 때문에 짧은 쪽을 고른다 — 한계 ③).
    - 같은 화자는 등급당 `max_per_speaker` 건까지 — 한 사람의 억양이 등급 수치를 대표하지 않게.
    - 입력 순서와 무관하게 같은 결과가 나오도록 이름순으로 정렬한 뒤 섞는다.
    """
    picked: dict[str, list[Sample]] = {}
    for level in levels:
        pool = sorted(
            (s for s in samples if s.level == level and min_sec <= s.seconds <= max_sec),
            key=lambda s: s.name,
        )
        random.Random(f"{seed}:{level}").shuffle(pool)
        chosen: list[Sample] = []
        per_speaker: dict[str, int] = {}
        for s in pool:
            if per_speaker.get(s.user_id, 0) >= max_per_speaker:
                continue
            chosen.append(s)
            per_speaker[s.user_id] = per_speaker.get(s.user_id, 0) + 1
            if len(chosen) >= per_level:
                break
        picked[level] = chosen
    return picked


def original_subset(picked: dict[str, list[Sample]], k: int) -> set[str]:
    """원본(48 kHz)으로도 잴 부분집합 — 등급별 앞 k 건. 표본 순서가 시드로 고정돼 있으므로 이것도 고정된다."""
    return {s.name for chosen in picked.values() for s in chosen[:k]}


def planned_seconds(picked: dict[str, list[Sample]], subset: set[str]) -> dict[str, float]:
    """예산 계산 — 8 kHz 전사는 전 표본, 원본 전사는 부분집합만."""
    narrow = sum(s.seconds for chosen in picked.values() for s in chosen)
    original = sum(s.seconds for chosen in picked.values() for s in chosen if s.name in subset)
    return {"narrow": narrow, "original": original, "total": narrow + original}


def raw_score_pairs(pairs: list[tuple[str, str]]) -> dict:
    """**정규화 전** WER/CER — 라벨·가설을 있는 그대로 대조한다. 정규화가 점수를 얼마나
    올렸는지 드러내려고 함께 낸다(정규화는 점수를 올리는 조치라 감추면 안 된다)."""
    pairs = [(r, h) for r, h in pairs if r.split()]
    if not pairs:
        return {"wer": float("nan"), "cer": float("nan"), "n": 0}
    w_err = sum(_edit_distance(r.split(), h.split()) for r, h in pairs)
    w_len = sum(len(r.split()) for r, _ in pairs)
    c_err = sum(_edit_distance(r.replace(" ", ""), h.replace(" ", "")) for r, h in pairs)
    c_len = sum(len(r.replace(" ", "")) for r, _ in pairs)
    return {"wer": w_err / w_len, "cer": c_err / c_len, "n": len(pairs)}


def raw_aggregate_by_group(rows: list[tuple[str, str, str]]) -> dict[str, dict]:
    groups: dict[str, list[tuple[str, str]]] = {}
    for group, ref, hyp in rows:
        groups.setdefault(group, []).append((ref, hyp))
    result = {g: raw_score_pairs(p) for g, p in sorted(groups.items())}
    result["__all__"] = raw_score_pairs([(r, h) for _, r, h in rows])
    return result


# ── 오디오 ──────────────────────────────────────────────────────────────

def extract_wav(name: str, zip_path: Path = WAV_ZIP, out_dir: Path = WORK_DIR / "wav") -> Path:
    """zip 에서 한 파일만 꺼낸다. 20 GB 를 풀지 않는다 — zip 은 임의 접근이 된다."""
    dst = out_dir / f"{name}.wav"
    if dst.exists():
        return dst
    out_dir.mkdir(parents=True, exist_ok=True)
    # 항목 이름이 `/` 로 시작한다. unzip 이 "stripped absolute path" 경고와 함께 떼어 낸다.
    # unzip 은 「절대 경로를 떼어 냈다」는 경고만으로 exit 1 을 돌려준다 — 성공 판정은 파일 존재로 한다.
    subprocess.run(
        ["unzip", "-o", "-q", str(zip_path), f"/{name}.wav", "-d", str(out_dir)],
        check=False, stderr=subprocess.DEVNULL,
    )
    if not dst.exists():
        raise SystemExit(f"zip 에 없다: /{name}.wav")
    return dst


def downsample(src: Path, dst: Path) -> Path:
    """ffmpeg 으로 8 kHz 모노 LINEAR16 사본. 파일명이 고유하므로(sound_id 포함) 덮어쓰기 사고는 없다."""
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src),
         "-ar", str(TARGET_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
        check=True,
    )
    return dst


def cache_key(content_key: str, model: str) -> str:
    """전사 캐시 키 = 오디오 내용 해시 + 모델. v1 은 접미 없이 둔다 — 09-21 첫 실측의 캐시 100건이
    그 이름으로 있어서, 바꾸면 같은 오디오를 v1 로 다시 사서 예산을 두 번 쓴다. 다른 모델은
    `<해시>-<모델>` 이라 v1 캐시와 절대 섞이지 않는다."""
    return content_key if model == "v1" else f"{content_key}-{model}"


def project_from_credentials(path: str | None) -> str:
    """서비스 계정 JSON 의 `project_id`. 파일이 없거나 읽을 수 없으면 빈 문자열 — 호출부가 멈춘다."""
    if not path:
        return ""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")).get("project_id") or ""
    except (OSError, json.JSONDecodeError):
        return ""


def model_slug(model: str) -> str:
    """파일명 접미 — `chirp_3` → `chirp3`. v1 은 접미 없음(첫 실측 파일명 그대로)."""
    return "" if model == "v1" else model.replace("_", "")


def output_paths(model: str, day: str, work_dir: Path = WORK_DIR, public_dir: Path = PUBLIC_DIR) -> tuple[Path, Path]:
    """(건별 결과 JSON, 공개 요약 JSON). 모델이 다르면 파일도 다르다 — v1 결과를 덮어쓰지 않는다."""
    suffix = f"-{model_slug(model)}" if model_slug(model) else ""
    return (work_dir / f"{day}-proficiency{suffix}.json",
            public_dir / f"a5-wer-{day}{suffix}.json")


def cached_transcribe(recognize, path: Path, budget: Budget, cache_dir: Path, model: str) -> tuple[str, bool]:
    """전사 결과를 내용 해시(+모델)로 캐시한다 — 재실행이 예산을 두 번 쓰지 않는다. (가설, 캐시 적중) 을 돌려준다.
    `recognize(path, meta) -> dict` 는 v1/v2 어느 쪽이든 같은 모양(`transcript`·`segments`)을 돌려준다."""
    meta = audio_meta(path)
    cache = cache_dir / f"{cache_key(file_key(path), model)}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["transcript"], True
    ok, why = budget.allows(meta.seconds)
    if not ok:
        raise SystemExit(f"COST-1 가드에 걸렸다(건별 확인): {why}")
    result = recognize(path, meta)
    budget.charge(meta.seconds)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({
        "source": str(path.relative_to(REPO_ROOT)), "seconds": round(meta.seconds, 2),
        "sample_rate": meta.rate, "channels": meta.channels, "stt_model": model,
        "transcribed_at": dt.datetime.now().isoformat(timespec="seconds"), **result,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return result["transcript"], False


def _git_commit() -> str | None:
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return f"{head}-dirty" if dirty else head
    except (subprocess.CalledProcessError, OSError):
        return None


# ── 리포트 ──────────────────────────────────────────────────────────────

def _fmt(s: dict) -> str:
    if not s or not s.get("n"):
        return "측정 불가 — 표본 없음"
    return f"WER {s['wer']:.3f} · CER {s['cer']:.3f} · n {s['n']}"


def _ordered(scores: dict[str, dict]) -> list[tuple[str, dict]]:
    return [(lv, scores[lv]) for lv in LEVELS if lv in scores] + [("__all__", scores["__all__"])]


def print_summary(picked: dict[str, list[Sample]], subset: set[str]) -> None:
    print(f"데이터 {DATASET} · 등급 {len(picked)} 개")
    for level, chosen in picked.items():
        speakers = {s.user_id for s in chosen}
        secs = sum(s.seconds for s in chosen)
        langs = sorted({s.language for s in chosen})
        tasks = sorted({s.task for s in chosen})
        print(f"  {level:>12}  n {len(chosen):>2} · 화자 {len(speakers):>2} · {secs:6.1f}초 "
              f"· 원본도 잼 {sum(1 for s in chosen if s.name in subset)} · 모어 {len(langs)}종 · 과제 {'/'.join(tasks)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="A-5 — 숙련도 등급별 WER/CER (8 kHz 주 측정, 원본 부분집합)")
    ap.add_argument("--per-level", type=int, default=20, help="등급당 표본 수")
    ap.add_argument("--seed", type=int, default=20260921, help="표본 추출 시드 — 재측정 때 같게 둔다")
    ap.add_argument("--min-sec", type=float, default=3.0, help="발화 길이 창 하한(초)")
    ap.add_argument("--max-sec", type=float, default=6.0, help="발화 길이 창 상한(초)")
    ap.add_argument("--max-per-speaker", type=int, default=2, help="같은 화자 최대 건수(등급당)")
    ap.add_argument("--original-subset", type=int, default=5, help="원본(48 kHz)으로도 잴 등급당 건수")
    ap.add_argument("--max-total-sec", type=float, default=550.0,
                    help="이 실행이 쓸 STT 초의 자체 상한. 넘으면 실측 전에 멈춘다(건수를 줄인다)")
    ap.add_argument("--stt-model", choices=STT_MODELS, default="v1",
                    help="v1 = Cloud Speech v1 기본 모델(09-21 첫 실측). chirp_3/chirp_2 = Speech-to-Text v2 지역 엔드포인트")
    ap.add_argument("--region", default=V2_DEFAULT_REGION,
                    help="v2 리전(chirp 모델에만 쓴다). Chirp 는 지역 엔드포인트에서만 된다")
    ap.add_argument("--probe", action="store_true",
                    help="첫 1건만 STT 로 보내 응답(모델·리전)을 확인하고 멈춘다. 예산은 그 1건만 쓴다")
    ap.add_argument("--dry-run", action="store_true", help="표본·총 길이만 출력하고 STT 를 부르지 않는다")
    ap.add_argument("--out", type=Path, default=None, help="건별 결과 JSON (기본: 날짜·모델로 정한다)")
    ap.add_argument("--public-out", type=Path, default=None, help="공개 요약 JSON (기본: 날짜·모델로 정한다)")
    args = ap.parse_args()
    default_out, default_public = output_paths(args.stt_model, dt.date.today().isoformat())
    args.out = args.out or default_out
    args.public_out = args.public_out or default_public

    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg 이 없다 —  brew install ffmpeg")
    if not WAV_ZIP.exists():
        raise SystemExit(f"wav zip 이 없다: {WAV_ZIP}")

    env = load_env(REPO_ROOT / ".env")
    os.environ.update({k: v for k, v in env.items() if k not in os.environ})

    labels = load_labels()
    picked = stratified_sample(labels, per_level=args.per_level, seed=args.seed,
                               min_sec=args.min_sec, max_sec=args.max_sec,
                               max_per_speaker=args.max_per_speaker)
    subset = original_subset(picked, args.original_subset)
    plan = planned_seconds(picked, subset)
    short = [lv for lv, chosen in picked.items() if len(chosen) < args.per_level]

    print_summary(picked, subset)
    print(f"계획(라벨 RecordedTime 기준) — 8kHz {plan['narrow']:.1f}초 + 원본 {plan['original']:.1f}초 "
          f"= {plan['total']:.1f}초 · 자체 상한 {args.max_total_sec:.0f}초")
    if short:
        print(f"⚠ 등급당 {args.per_level}건을 못 채운 등급: {', '.join(short)} — 리포트에 n 이 그대로 나간다")

    # 캡은 **프로세스 환경변수가 .env 를 이긴다** — 하루만 캡을 올릴 때 .env 를 고치지 않고
    # `STT_MAX_SECONDS_PER_DAY=900 ...` 로 준다. 그 사실은 리포트(`cap_override`)에 남긴다.
    budget = Budget(int(os.environ.get("STT_MAX_SECONDS_PER_DAY") or 0),
                    int(os.environ.get("STT_MAX_SECONDS_PER_MONTH") or 0))
    cap_override = {k: {"env_file": int(env.get(k) or 0), "process": int(os.environ.get(k) or 0)}
                    for k in ("STT_MAX_SECONDS_PER_DAY", "STT_MAX_SECONDS_PER_MONTH")
                    if (env.get(k) or "0") != (os.environ.get(k) or "0")}
    print(f"장부 — 오늘 {budget.used_today:.0f}/{budget.per_day}초 · 이번 달 {budget.used_month:.0f}/{budget.per_month}초")
    if cap_override:
        print(f"⚠ 캡을 프로세스 환경변수로 덮어썼다(.env 는 그대로): {cap_override}")
    allowed, why = budget.allows(plan["total"])
    if not allowed:
        raise SystemExit(f"COST-1 가드에 걸렸다: {why}")
    if plan["total"] > args.max_total_sec:
        raise SystemExit(f"자체 상한 초과: {plan['total']:.0f} > {args.max_total_sec:.0f}초 — --per-level 을 줄여라")
    if args.dry_run:
        print("--dry-run — STT 를 부르지 않았다")
        return 0

    if args.stt_model == "v1":
        from google.cloud import speech  # noqa: PLC0415
        client = speech.SpeechClient()

        def recognize(path: Path, meta):
            return transcribe(client, speech, path, meta)
        stt_desc = {"api": "google-cloud-speech v1 recognize", "language": "ko-KR", "model": "default",
                    "automatic_punctuation": True}
    else:
        from google.cloud import speech_v2  # noqa: PLC0415
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or project_from_credentials(
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
        if not project:
            raise SystemExit("프로젝트 ID 가 없다 — GOOGLE_CLOUD_PROJECT 를 주거나 서비스 계정 JSON 에 project_id 가 있어야 한다")
        client = speech_v2_client(speech_v2, args.region)

        def recognize(path: Path, meta):
            return transcribe_v2(client, speech_v2, path, project=project, region=args.region, model=args.stt_model)
        stt_desc = {"api": "google-cloud-speech v2 recognize (recognizers/_)", "language": "ko-KR",
                    "model": args.stt_model, "region": args.region, "decoding": "auto_decoding_config",
                    "automatic_punctuation": True}
    cache_dir = WORK_DIR / "stt"
    used_before = budget.used_today

    rows_norm: list[tuple[str, str, str]] = []      # (조건/등급, 정답, 가설) — 정규화는 채점기가 한다
    rows_raw: list[tuple[str, str, str]] = []
    items: list[dict] = []
    cache_hits = 0
    total = sum(len(c) for c in picked.values())
    i = 0
    for level in LEVELS:
        for s in picked.get(level, []):
            i += 1
            src = extract_wav(s.name)
            narrow = downsample(src, WORK_DIR / "8k" / f"{s.name}.wav")
            ref = normalize_71479(s.reference)
            item = {**asdict(s), "wav_seconds": round(audio_meta(src).seconds, 2), "conditions": {}}
            conds = [(f"{TARGET_RATE}Hz", narrow)]
            if s.name in subset:
                conds.append(("original", src))
            for cond, path in conds:
                hyp, hit = cached_transcribe(recognize, path, budget, cache_dir, args.stt_model)
                cache_hits += hit
                if args.probe:
                    print(f"--probe — {args.stt_model}@{args.region if args.stt_model != 'v1' else 'v1'} "
                          f"응답 받음: {s.name} ({cond}, 캐시 {'적중' if hit else '없음'})")
                    print(f"  정답: {ref}")
                    print(f"  가설: {hyp!r}")
                    print(f"  STT 사용 — 오늘 {budget.used_today:.1f}/{budget.per_day}초")
                    return 0
                meta = audio_meta(path)
                item["conditions"][cond] = {"rate": meta.rate, "transcript": hyp}
                rows_norm.append((f"{cond}|{level}", ref, hyp))
                rows_raw.append((f"{cond}|{level}", s.reference, hyp))
                if s.name in subset and cond == f"{TARGET_RATE}Hz":
                    rows_norm.append((f"{TARGET_RATE}Hz-subset|{level}", ref, hyp))
                    rows_raw.append((f"{TARGET_RATE}Hz-subset|{level}", s.reference, hyp))
            items.append(item)
            print(f"  [{i}/{total}] {level:>12} {s.name}  (오늘 {budget.used_today:.0f}초)")

    # 조건별 → 등급별 집계. 정규화 후(채점기 규칙 + 71479 추가 규칙) / 정규화 전.
    conditions = [f"{TARGET_RATE}Hz", f"{TARGET_RATE}Hz-subset", "original"]
    scores = {"normalized": {}, "raw": {}}
    for cond in conditions:
        norm_rows = [(g.split("|", 1)[1], r, h) for g, r, h in rows_norm if g.startswith(cond + "|")]
        raw_rows = [(g.split("|", 1)[1], r, h) for g, r, h in rows_raw if g.startswith(cond + "|")]
        scores["normalized"][cond] = aggregate_by_group(norm_rows)
        scores["raw"][cond] = raw_aggregate_by_group(raw_rows)
    empty = sum(1 for it in items for c in it["conditions"].values() if not c["transcript"].strip())

    used_after = budget.used_today
    print("\n" + "=" * 72)
    model_label = "Google STT v1 기본 모델" if args.stt_model == "v1" else f"Google STT v2 {args.stt_model} @ {args.region}"
    print(f"A-5 — 숙련도 등급별 WER/CER ({model_label} · ko-KR · 8 kHz 주 측정)")
    print("=" * 72)
    for cond in conditions:
        print(f"\n[{cond}]  정규화 후  /  정규화 전")
        for lv, s in _ordered(scores["normalized"][cond]):
            r = scores["raw"][cond].get(lv, {})
            print(f"  {lv:>12}  {_fmt(s):<36}  /  {_fmt(r)}")
    sub, orig = scores["normalized"][f"{TARGET_RATE}Hz-subset"], scores["normalized"]["original"]
    print(f"\n원본 vs 8kHz (같은 {orig['__all__']['n']}건, 정규화 후):")
    for lv, o in _ordered(orig):
        n = sub.get(lv, {})
        if o.get("n") and n.get("n"):
            print(f"  {lv:>12}  WER {o['wer']:.3f} → {n['wer']:.3f} ({n['wer'] - o['wer']:+.3f}) "
                  f"· CER {o['cer']:.3f} → {n['cer']:.3f} ({n['cer'] - o['cer']:+.3f})")
    print(f"\n빈 가설(STT 가 아무것도 못 알아들음) {empty}건 · 캐시 적중 {cache_hits}회")
    print(f"STT 사용 — 이 실행 {used_after - used_before:.1f}초 · 오늘 {used_after:.1f}/{budget.per_day}초 "
          f"· 이번 달 {budget.used_month:.1f}/{budget.per_month}초")
    print("\n적용한 정규화(채점기):")
    for rule in NORMALIZATION_RULES:
        print(f"  - {rule}")
    print("추가한 정규화(71479 라벨):")
    for rule in EXTRA_NORMALIZATION_RULES:
        print(f"  - {rule}")
    print("\n⚠ 이 수치는 **상한**이다 — 온라인 녹음을 다운샘플만 했고(코덱·잡음 없음), 과제가 질문답변·")
    print("  낭독이라 민원 어휘가 아니며, 3~6초 짧은 발화만 골랐다. 실제 통화에서는 더 나쁘다.")

    limits = [
        "온라인 녹음(48 kHz, 잡음 없음)을 다운샘플만 했다 — 실제 전화망(코덱·잡음·라인 손실)보다 좋다 → 상한",
        "과제가 질문답변(ATQ)·낭독(LAR) 등이라 민원 어휘가 아니다",
        f"STT 예산 때문에 {args.min_sec:.0f}~{args.max_sec:.0f}초 짧은 발화만 골랐다(데이터 중앙값 7.5초)",
        "모어 분포가 인도네시아·베트남에 편중돼 있다(데이터셋 자체의 분포)",
        f"등급당 n={args.per_level} — 등급 간 차이가 표본 잡음보다 작을 수 있다. 원본 재측정은 등급당 {args.original_subset}건뿐",
        "숫자 표기(라벨 `십오년` vs STT `15년`)와 `%` 는 정규화하지 않았다 — 그만큼 오류로 잡힌다",
        ("STT 모델은 Google Cloud Speech v1 `recognize` 기본 모델(ko-KR)이다 — 09-09 8 kHz 실험과 같은 호출. 티켓의 「Chirp 3」 표기와 다르다"
         if args.stt_model == "v1" else
         f"STT 모델은 Speech-to-Text v2 `{args.stt_model}`(리전 {args.region}, 암묵 인식기, auto decoding)이다 — 표본·8 kHz 사본은 v1 실측과 같다"),
    ]
    if args.original_subset == 0:
        limits.append("원본(48 kHz) 재측정은 하지 않았다(--original-subset 0, 예산) — `original` 조건은 표본 0건")
    if cap_override:
        limits.append(f"STT 캡을 이 실행에서만 프로세스 환경변수로 덮어썼다(.env 는 그대로): {cap_override}")
    meta = {
        "measured_at": dt.date.today().isoformat(),
        "commit": _git_commit(),
        "command": "PYTHONPATH= .venv/bin/python scripts/measure_a5_proficiency.py " + " ".join(sys.argv[1:]),
        "dataset": DATASET,
        "stt": stt_desc,
        "stt_model": args.stt_model,
        "seed": args.seed,
        "design": {"per_level": args.per_level, "min_sec": args.min_sec, "max_sec": args.max_sec,
                   "max_per_speaker": args.max_per_speaker, "original_subset_per_level": args.original_subset,
                   "target_rate_hz": TARGET_RATE, "source_rate_hz": 48000},
        "sample": {lv: {"n": len(c), "speakers": len({s.user_id for s in c}),
                        "label_seconds": round(sum(s.seconds for s in c), 1),
                        "languages": sorted({s.language for s in c}), "tasks": sorted({s.task for s in c})}
                   for lv, c in picked.items()},
        "stt_seconds": {"this_run": round(used_after - used_before, 1), "today_after": round(used_after, 1),
                        "month_after": round(budget.used_month, 1), "cache_hits": cache_hits,
                        "cap_per_day": budget.per_day, "cap_per_month": budget.per_month,
                        "cap_override": cap_override},
        "empty_hypotheses": empty,
        "normalization": {"base": list(NORMALIZATION_RULES), "extra_71479": list(EXTRA_NORMALIZATION_RULES)},
        "limits": limits,
        "note": "이 수치는 상한이다. 목표치가 아니라 측정값이다(절대 원칙 2·10). 조건: 8000Hz(전 표본) · "
                "8000Hz-subset(원본과 같은 건) · original(48 kHz). 각각 정규화 후/전.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({**meta, "scores": scores, "items": items},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    args.public_out.parent.mkdir(parents=True, exist_ok=True)
    args.public_out.write_text(json.dumps({**meta, "scores": scores}, ensure_ascii=False, indent=1),
                               encoding="utf-8")
    print(f"\n결과: {args.out.relative_to(REPO_ROOT)}  (전사 원문 포함 — .gitignore 대상, AI Hub 재배포 금지)")
    print(f"공개 요약: {args.public_out.relative_to(REPO_ROOT)}  (건별 전사 없음)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
