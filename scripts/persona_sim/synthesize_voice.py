#!/usr/bin/env python3
# Requirement: D-5
"""합성 대본 → **발화별 8kHz 모노 WAV**(macOS `say`). D-5 통화 온도의 **배선·채점 경로**를 확인하기 위한 합성 음성이다.

    python3 scripts/persona_sim/synthesize_voice.py                 # 전 대본
    python3 scripts/persona_sim/synthesize_voice.py SYN-011 SYN-012

출력: `data/processed/synthetic-voice/dasan-v0/<SYN-id>/<seq>-<speaker>.wav` + `manifest.json` (gitignore — 커밋하지 않는다)

## 톤을 어떻게 연기하나
`tone` 을 `say` 내장 명령 **`[[volm]]`(크기)·`[[rate]]`(빠르기)** 로 바꾼다. **높이(`[[pbas]]`)는 쓰지 않는다** —
2026-09-17 음성 4종으로 재 보니 8kHz 에서 F0 추정이 음성마다 옥타브 오류로 뒤집혔고(같은 명령에 61Hz~400Hz), 크기는
일관되게 움직였다(작게 −47dB · 보통 −37dB · 크게 −20dB).
평상시 턴이 전부 같은 크기면 기준선 폭(MAD)이 0 에 붙어 작은 차이도 「튐」이 된다 — **시드를 고정한 작은 흔들림**을 준다.

## ⚠ 이것으로 말할 수 없는 것 (절대 원칙 10)
여기서 나온 채점은 **「우리가 크기를 바꿔 넣은 턴을 규칙이 찾는가」** 다. 실제 사람의 격앙(목소리 높이·떨림·말 끊김)은
TTS 가 흉내 내지 못한다. **D-5 의 실제 성능이 아니라 배선과 판정 규칙의 동작 확인**으로만 인용한다.
자체 녹음이 아니다(절대 원칙 7) — 사람의 목소리가 들어가지 않는다.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "persona_sim" / "dasan-v0"
OUT = ROOT / "data" / "processed" / "synthetic-voice" / "dasan-v0"
SEED = 20260917
SAMPLE_RATE = 8000  # 실제 통화(다산콜DB·저품질전화)와 같은 협대역

# tone → (크기 0~1, 분당 단어). 크기 흔들림은 평상시 ±0.04 — 아래 `_JITTER`
TONE_PROSODY = {
    "calm": (0.50, 185),
    "tense": (0.60, 200),
    "raised": (0.75, 215),
    "shouting": (1.00, 235),
    "weary": (0.22, 140),
}
_JITTER = 0.04
FALLBACK_VOICE = "Yuna"


def korean_voices() -> dict[str, str]:
    """짧은 이름 → `say -v` 전체 이름. 같은 짧은 이름의 영어 음성이 있어 전체 이름으로 불러야 한다."""
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=True).stdout
    voices = {}
    for line in out.splitlines():
        head, _, rest = line.partition("  ")
        if "ko_KR" in rest or "ko_KR" in line.split("#")[0]:
            full = line.split("  ")[0].strip()
            voices[full.split(" (")[0]] = full
    return voices


def synthesize(script_id: str, personas: dict, voices: dict[str, str], rng: random.Random) -> dict:
    data = json.loads((SCRIPTS / f"{script_id}.json").read_text(encoding="utf-8"))
    out_dir = OUT / script_id
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"id": script_id, "seed": SEED, "sample_rate": SAMPLE_RATE, "turns": []}
    for turn in data["turns"]:
        persona_id = data["agent_persona"] if turn["speaker"] == "agent" else data["customer_persona"]
        voice = voices.get(personas.get(persona_id, {}).get("say_voice", ""), voices.get(FALLBACK_VOICE, FALLBACK_VOICE))
        volume, rate = TONE_PROSODY[turn["tone"]]
        volume = min(1.0, max(0.05, volume + rng.uniform(-_JITTER, _JITTER)))
        wav = out_dir / f"{turn['seq']:02d}-{turn['speaker']}.wav"
        with tempfile.TemporaryDirectory() as tmp:
            aiff = Path(tmp) / "t.aiff"
            subprocess.run(["say", "-v", voice, "-o", str(aiff), f"[[volm {volume:.2f}]][[rate {rate}]] {turn['text']}"], check=True)
            subprocess.run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{SAMPLE_RATE}", "-c", "1", str(aiff), str(wav)], check=True)
        manifest["turns"].append({"seq": turn["seq"], "speaker": turn["speaker"], "tone": turn["tone"],
                                  "voice": voice, "volm": round(volume, 3), "rate": rate, "wav": wav.name})
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def main() -> int:
    if sys.platform != "darwin":
        print("macOS say·afconvert 가 필요하다", file=sys.stderr)
        return 2
    personas = json.loads((SCRIPTS / "personas.json").read_text(encoding="utf-8"))
    personas = {**personas["agents"], **personas["customers"]}
    ids = sys.argv[1:] or sorted(p.stem for p in SCRIPTS.glob("SYN-*.json"))
    voices = korean_voices()
    rng = random.Random(SEED)  # 대본 순서대로 같은 흔들림 — 재현 가능
    for script_id in ids:
        m = synthesize(script_id, personas, voices, rng)
        print(f"{script_id}: {len(m['turns'])}개 발화 → {OUT / script_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
