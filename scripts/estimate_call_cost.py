#!/usr/bin/env python3
# Requirement: COST-1, B-4
"""통화 1건당 토큰·생성 시간·STT 초 — **추정**이다 (`w7-token-cost`). 실제 통화를 재지 않았다.

재료(전부 이미 잰 값이다 — 여기서 새로 지어내는 수는 없다):
- 생성 1회 토큰·지연: `scripts/eval_generation.py` 결과 JSON(골든셋 96문항, 로컬 Ollama)
- 통화당 트리거 수: 트리거 v1 은 **고객의 확정 발화마다** 발동한다(`retrieval/domain/services/trigger.py`) →
  AI Hub 다산 대화셋 1,009개의 **고객 턴 수**로 대신한다
- 발화 길이: `data/processed/call-temperature/hypothesis.json` 의 역할별 발화 길이 중앙값(다산콜DB — ⚠ 연기된 시나리오 음성)
- STT 캡: `infra/k8s/base/gateway.yaml` 의 `STT_MAX_SECONDS_PER_DAY`·`_MONTH`

⚠ **API 요금표를 곱하지 않는다** — 생성은 로컬 Ollama 라 우리가 내는 토큰 요금이 없다. 돈이 나가는 곳은 GPU 점유 시간과 Google STT 다.
⚠ STT 초는 **발화 길이의 합**이다 — 침묵·대기음이 빠져 실제 스트림 시간보다 **짧다**(하한).

    .venv/bin/python scripts/estimate_call_cost.py
"""

from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "data" / "processed" / "generation-eval" / "2026-09-15-kanana-1.5-2.1b-instruct_q4_k_m-noschema.json"


def main() -> int:
    gen = json.loads(GEN.read_text())
    s = gen["summary"]
    turns: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for f in sorted((ROOT / "data" / "raw" / "aihub-minwon-qa" / "validation" / "label" / "다산콜센터").glob("*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            turns[r["대화셋일련번호"]][r["화자"]] += 1
    cust = sorted(t["고객"] for t in turns.values())
    agent = sorted(t["상담사"] for t in turns.values())
    dur = json.loads((ROOT / "data" / "processed" / "call-temperature" / "hypothesis.json").read_text())["summary"]
    gw = (ROOT / "infra" / "k8s" / "base" / "gateway.yaml").read_text()
    cap_day = int(re.search(r"STT_MAX_SECONDS_PER_DAY, value: \"(\d+)\"", gw).group(1))
    cap_month = int(re.search(r"STT_MAX_SECONDS_PER_MONTH, value: \"(\d+)\"", gw).group(1))

    triggers_mean, triggers_p90 = statistics.mean(cust), cust[int(len(cust) * 0.9)]
    per_gen_tokens = s["prompt_tokens_mean"] + s["output_tokens_mean"]
    per_gen_tokens_max = s["prompt_tokens_max"] + s["output_tokens_max"]
    gen_p50_s = s["latency_ms"]["p50"] / 1000
    stt_s = statistics.mean(cust) * dur["민원인"]["duration_median_s"] + statistics.mean(agent) * dur["상담사"]["duration_median_s"]

    print(f"재료: 생성 {gen['meta']['model']} · {gen['meta']['questions']}문항 · 커밋 {gen['meta']['commit']} · AI Hub 대화셋 {len(turns)}개 · STT 캡 일 {cap_day}s / 월 {cap_month}s")
    print(f"통화당 트리거(고객 턴): 평균 {triggers_mean:.2f} · p90 {triggers_p90}")
    print(f"생성 1회: 입력 {s['prompt_tokens_mean']:.0f} + 출력 {s['output_tokens_mean']:.0f} 토큰(최대 {per_gen_tokens_max}) · p50 {gen_p50_s:.2f}s")
    print(f"[추정] 통화 1건 생성 토큰: 평균 {triggers_mean * per_gen_tokens:,.0f} · 나쁜 경우(p90 턴 × 최대 토큰) {triggers_p90 * per_gen_tokens_max:,.0f}")
    print(f"[추정] 통화 1건 GPU 생성 시간(상위 1건, NUM_PARALLEL=1): {triggers_mean * gen_p50_s:.1f}s")
    print(f"[추정·하한] 통화 1건 STT 초(발화 길이 합): {stt_s:.0f}s → 일 캡 {cap_day / stt_s:.1f}건 · 월 캡 {cap_month / stt_s:.1f}건")
    print(f"[추정] GPU 생성 점유율(통화 1건): {triggers_mean * gen_p50_s / stt_s:.1%} → 평균만 보면 동시 {stt_s / (triggers_mean * gen_p50_s):.0f}통화까지 큐가 쌓이지 않는다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
