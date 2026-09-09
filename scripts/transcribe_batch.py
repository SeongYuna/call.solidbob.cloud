#!/usr/bin/env python3
# Requirement: A-1 (STT), COST-1 (STT 사용량 이중 캡)
"""AI Hub 오디오를 파일 단위(배치)로 전사한다. 실시간 스트리밍은 3주차(A-1)다.

왜 배치가 먼저인가
    반복 실험을 스트리밍으로 돌리면 할당량(STT_MAX_SECONDS_PER_DAY=600)을 금방 태운다.
    한 번 전사해 저장해두면 같은 오디오를 검색·트리거·마스킹 실험에 몇 번이고 다시 쓸 수 있다.
    같은 파일을 다시 요청하면 캐시에서 꺼내므로 할당량을 두 번 쓰지 않는다.

COST-1 — 애플리케이션 가드 (2차 방어선)
    1차는 GCP 콘솔 쿼터 하드 리밋이다. 이 스크립트는 그 앞단에서 한 번 더 막는다.
    data/processed/stt-usage.json 에 날짜별 사용 초를 누적하고, .env 의
    STT_MAX_SECONDS_PER_DAY / _MONTH 를 넘기면 **새 요청을 보내지 않는다.**
    캡을 넘길 것 같은 파일은 건너뛰고 계속 진행한다(중간에 죽지 않는다).

SEC-2 — 자격증명
    .env 의 GOOGLE_APPLICATION_CREDENTIALS 는 **경로만** 읽는다. 키 파일 내용은 열지 않고
    출력하지도 않는다.

주의 — 전사 결과에는 개인정보가 그대로 들어 있다
    출력은 data/processed/ 아래에 쓴다(.gitignore 대상). **저장소에 커밋하지 않는다.**
    화면 표시·DB 저장 앞단의 마스킹(C-5)은 별도 모듈이며 이 스크립트의 책임이 아니다.

사용법
    python3 scripts/transcribe_batch.py --dry-run                 # 쓸 초만 계산, 요청 안 보냄
    python3 scripts/transcribe_batch.py data/raw/aihub-*/**/*.wav
    python3 scripts/transcribe_batch.py --manifest files.txt --limit 20
"""

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import sys
import wave
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "processed" / "stt"
USAGE_FILE = REPO_ROOT / "data" / "processed" / "stt-usage.json"

LANGUAGE = "ko-KR"
DEFAULT_SAMPLE_RATE = 8000          # AI Hub 상담 음성은 8kHz 모노 (V1 확인)


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


class AudioMeta(NamedTuple):
    seconds: float
    rate: int
    channels: int


def audio_meta(path: Path) -> AudioMeta:
    """wav 헤더에서 길이·샘플레이트·채널을 읽는다.

    길이는 요청 전에 캡을 지키려고 필요하고, **샘플레이트·채널은 요청 자체에 필요하다.**
    전에는 길이만 읽고 샘플레이트는 --sample-rate 기본값(8000)을 그대로 보냈다.
    실제 파일이 16kHz 거나 스테레오면 구글은 엉뚱한 전사를 돌려주고 **요금은 그대로 나간다.**
    헤더에 답이 있는데 안 읽을 이유가 없다.
    """
    try:
        with contextlib.closing(wave.open(str(path), "rb")) as w:
            rate = w.getframerate() or DEFAULT_SAMPLE_RATE
            return AudioMeta(w.getnframes() / float(rate), rate, w.getnchannels() or 1)
    except (wave.Error, EOFError, OSError):
        return AudioMeta(0.0, 0, 0)


def file_key(path: Path) -> str:
    """내용 기준 캐시 키. 경로가 바뀌어도 같은 오디오면 다시 전사하지 않는다."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ─────────────────────────────────────────────── COST-1 사용량 원장

class Budget:
    def __init__(self, per_day: int, per_month: int) -> None:
        self.per_day = per_day
        self.per_month = per_month
        self.today = dt.date.today().isoformat()
        self.month = self.today[:7]
        self.ledger: dict[str, float] = {}
        if USAGE_FILE.exists():
            try:
                self.ledger = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.ledger = {}

    @property
    def used_today(self) -> float:
        return self.ledger.get(self.today, 0.0)

    @property
    def used_month(self) -> float:
        return sum(v for k, v in self.ledger.items() if k.startswith(self.month))

    def allows(self, seconds: float) -> tuple[bool, str]:
        if self.per_day and self.used_today + seconds > self.per_day:
            return False, (f"일 한도 초과 ({self.used_today:.0f}+{seconds:.0f}"
                           f" > {self.per_day}초)")
        if self.per_month and self.used_month + seconds > self.per_month:
            return False, (f"월 한도 초과 ({self.used_month:.0f}+{seconds:.0f}"
                           f" > {self.per_month}초)")
        return True, ""

    def charge(self, seconds: float) -> None:
        self.ledger[self.today] = self.used_today + seconds
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps(self.ledger, indent=2, sort_keys=True),
                              encoding="utf-8")


# ─────────────────────────────────────────────── 전사

def transcribe(client, speech, path: Path, meta: "AudioMeta") -> dict:
    with open(path, "rb") as f:
        content = f.read()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=meta.rate,             # 헤더 값. 추측하면 요금만 내고 결과를 버린다
        audio_channel_count=meta.channels,       # 스테레오를 모노로 보내면 전사가 깨진다
        language_code=LANGUAGE,
        enable_word_time_offsets=True,   # 발화 종료 시각 — 골든셋 스펙에 필요
        enable_automatic_punctuation=True,
    )
    resp = client.recognize(config=config, audio=speech.RecognitionAudio(content=content))

    segments = []
    for result in resp.results:
        alt = result.alternatives[0]
        words = [{"word": w.word,
                  "start_ms": int(w.start_time.total_seconds() * 1000),
                  "end_ms": int(w.end_time.total_seconds() * 1000)}
                 for w in alt.words]
        segments.append({
            "transcript": alt.transcript,
            "confidence": round(alt.confidence, 4),
            "end_ms": words[-1]["end_ms"] if words else None,
            "words": words,
        })
    return {"segments": segments,
            "transcript": " ".join(s["transcript"] for s in segments).strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="전사할 wav 파일")
    ap.add_argument("--manifest", help="파일 목록이 한 줄에 하나씩 든 텍스트")
    ap.add_argument("--limit", type=int, help="앞에서 N개만")
    ap.add_argument("--sample-rate", type=int,
                    help="wav 헤더 대신 이 값을 쓴다 (헤더가 틀린 파일용 — 보통 필요 없다)")
    ap.add_argument("--dry-run", action="store_true",
                    help="쓸 초만 계산하고 요청은 보내지 않는다")
    ap.add_argument("--force", action="store_true", help="캐시를 무시하고 다시 전사")
    args = ap.parse_args()

    files = [Path(p) for p in args.paths]
    if args.manifest:
        files += [Path(ln.strip()) for ln in Path(args.manifest).read_text(
            encoding="utf-8").splitlines() if ln.strip()]
    files = [f for f in files if f.suffix.lower() == ".wav" and f.is_file()]
    if args.limit:
        files = files[:args.limit]
    if not files:
        print("전사할 wav 파일이 없습니다. 경로나 --manifest 를 확인하세요.")
        return 1

    env = load_env(REPO_ROOT / ".env")
    budget = Budget(int(env.get("STT_MAX_SECONDS_PER_DAY", 0) or 0),
                    int(env.get("STT_MAX_SECONDS_PER_MONTH", 0) or 0))

    print(f"대상 {len(files)}개 · 오늘 사용 {budget.used_today:.0f}/{budget.per_day}초 "
          f"· 이번 달 {budget.used_month:.0f}/{budget.per_month}초")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = speech = None
    if not args.dry_run:
        cred = env.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        project = env.get("GOOGLE_CLOUD_PROJECT", "")
        if not cred or not project or not Path(cred).exists():
            print("실패: .env 의 GOOGLE_APPLICATION_CREDENTIALS / GOOGLE_CLOUD_PROJECT 확인 필요")
            return 1
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred   # 경로만. 내용은 읽지 않는다
        os.environ["GOOGLE_CLOUD_PROJECT"] = project
        try:
            from google.cloud import speech as speech_mod
        except ImportError:
            print("실패: google-cloud-speech 미설치 — pip install google-cloud-speech==2.40.0")
            return 1
        speech = speech_mod
        client = speech.SpeechClient()

    done = cached = skipped = failed = 0
    planned = 0.0        # 캡을 지키며 이번 실행이 실제로 쓸 초
    total_seconds = 0.0  # 캡과 무관한 대상 전체 길이 (남의 계산과 대조하는 값)
    too_long = 0
    rates: dict[tuple[int, int], int] = {}
    dry_used = 0.0       # dry-run 에서 charge() 대신 누적하는 가상 사용량

    for path in files:
        meta = audio_meta(path)
        if args.sample_rate:
            meta = meta._replace(rate=args.sample_rate)
        seconds = meta.seconds
        if seconds <= 0:
            print(f"  건너뜀 (wav 헤더를 읽을 수 없음): {path}")
            failed += 1
            continue
        total_seconds += seconds
        rates[(meta.rate, meta.channels)] = rates.get((meta.rate, meta.channels), 0) + 1

        # v1 동기 recognize 는 60초·10MB 가 상한이다. 넘으면 요청이 실패한다
        # (긴 파일은 long_running_recognize + GCS 가 필요하다).
        if seconds > 60:
            print(f"  건너뜀 (60초 초과 — v1 동기 recognize 한도): {path.name} [{seconds:.0f}초]")
            too_long += 1
            continue

        out_path = OUT_DIR / f"{file_key(path)}.json"
        if out_path.exists() and not args.force:
            cached += 1
            continue

        # dry-run 은 charge() 를 안 하므로 캡이 영원히 0 이다 — 가상 사용량을 더해 준다.
        # 이걸 안 하면 "새로 쓸 초" 가 캡을 무시한 전체 길이로 나와서, 실제 실행이
        # 하루 600초에서 멈춘다는 사실이 안 보인다.
        ok, why = budget.allows(dry_used + seconds if args.dry_run else seconds)
        if not ok:
            print(f"  건너뜀 ({why}): {path.name} [{seconds:.0f}초]")
            skipped += 1
            continue

        planned += seconds
        if args.dry_run:
            dry_used += seconds
            continue

        try:
            result = transcribe(client, speech, path, meta)
        except Exception as exc:                      # API 오류로 배치 전체가 죽지 않게
            print(f"  실패: {path.name} — {type(exc).__name__}: {exc}")
            failed += 1
            continue

        budget.charge(seconds)
        out_path.write_text(json.dumps({
            "source": str(path.relative_to(REPO_ROOT)) if path.is_absolute() else str(path),
            "seconds": round(seconds, 2),
            "language": LANGUAGE,
            "sample_rate": meta.rate,
            "channels": meta.channels,
            "transcribed_at": dt.datetime.now().isoformat(timespec="seconds"),
            **result,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        done += 1
        print(f"  전사: {path.name} [{seconds:.0f}초] → {out_path.name}")

    print(f"\n전사 {done} · 캐시 {cached} · 한도로 건너뜀 {skipped} "
          f"· 60초 초과 {too_long} · 실패 {failed}")
    if rates:
        fmt = " · ".join(f"{r}Hz/{c}ch {n}개" for (r, c), n in sorted(rates.items()))
        print(f"헤더: {fmt}")
    if args.dry_run:
        print(f"--dry-run: 대상 전체 {total_seconds:.0f}초 "
              f"({total_seconds / 3600:.1f}시간, {len(files)}건)")
        print(f"--dry-run: 이번 실행이 실제로 쓸 초 {planned:.0f} "
              f"(캡 {budget.per_day}초/일 · {budget.per_month}초/월 적용 후)")
        remaining = total_seconds - planned
        if remaining > 0:
            print(f"           남는 {remaining:.0f}초는 캡에 막혀 이번 실행에서 처리되지 않는다")
    else:
        print(f"오늘 사용 {budget.used_today:.0f}/{budget.per_day}초 · "
              f"이번 달 {budget.used_month:.0f}/{budget.per_month}초")
    print(f"출력: {OUT_DIR.relative_to(REPO_ROOT)}/  (.gitignore 대상 — 커밋하지 않는다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
