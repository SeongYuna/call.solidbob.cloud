# Requirement: A-1, E-1
"""STT 비교 — Google STT v1(2026-09-09 실측, data/processed/bandwidth-penalty/result.json) 과 **같은 20발화 · 같은 8kHz 사본 · 같은 정규화 · 같은 WER/CER 함수**로
온프레미스 대안 Whisper(faster-whisper, CPU int8)를 잰다. Google 은 다시 부르지 않는다(비용 — 저장된 전사를 쓴다).
⚠ 배치 전사 비교다(스트리밍 아님) · AI Hub 「고객 응대 음성」 16kHz 를 8kHz 로 낮춘 것 — 실제 전화망보다 좋다.
실행: <별도 venv>/bin/python eval/review-2026-10/stt_whisper_compare.py small large-v3-turbo
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps")]
from evaluation.metrics.asr import normalize_hypothesis, normalize_reference, score_pairs  # noqa: E402
import subprocess  # noqa: E402
import numpy as np  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402


def load16k(path):  # 8kHz 사본을 Whisper 입력 규격 16kHz float32 로 — PyAV 버전 충돌을 피해 ffmpeg 로 직접 푼다
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0

base = json.load(open(ROOT / "data/processed/bandwidth-penalty/result.json"))
items = base["items"]
def narrow(wav):  # 측정 스크립트가 만든 8kHz 사본
    p = ROOT / wav; return ROOT / "data/processed/bandwidth-penalty/8k" / f"{p.parts[-4]}_{p.parts[-3]}_{p.parts[-2]}_{p.stem}.wav"
out = {"dataset": base["dataset"], "n": len(items), "google_stt_v1_8k": base["scores"]["8000Hz"]}
g_pairs = [(it["reference"], it["8000Hz"]["transcript"]) for it in items]
out["google_stt_v1_8k_recomputed"] = score_pairs(g_pairs)
for name in sys.argv[1:]:
    m = WhisperModel(name, device="cpu", compute_type="int8")
    pairs, secs, audio = [], 0.0, 0.0
    for it in items:
        t0 = time.time()
        segs, info = m.transcribe(load16k(narrow(it["wav"])), language="ko", beam_size=5, vad_filter=False)
        hyp = " ".join(s.text.strip() for s in segs)
        secs += time.time() - t0; audio += info.duration
        pairs.append((it["reference"], hyp))
    sc = score_pairs(pairs)
    out[f"whisper-{name}"] = {**sc, "cpu_seconds": round(secs, 1), "audio_seconds": round(audio, 1), "real_time_factor": round(secs / audio, 2)}
    print(name, json.dumps(out[f"whisper-{name}"], ensure_ascii=False), flush=True)
print("google", json.dumps(out["google_stt_v1_8k_recomputed"], ensure_ascii=False))
(ROOT / "eval/review-2026-10/results/stt_whisper_compare.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
