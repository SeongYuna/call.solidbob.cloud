# Requirement: C-5, E-1
"""발표자료 ▢ 작업 2 — NER 교체(koelectra-ner → korean-pii-ner-v3) 전후 **마스킹 단계** 지연·메모리.

⚠ 722ms(서버 내부 p95)는 **트리거 발동 → 검색 → 카드 완성** 구간이고(`recommendation_interactor.py`) 마스킹을 포함하지 않는다.
그래서 같은 구간을 다시 재는 대신, 교체가 실제로 닿는 **마스킹 단계**를 운영과 같은 조립(`provider.build_masking_provider`
+ `RuleMaskingAdapter`)으로 잰다. 구성 하나 = 프로세스 하나(모델을 한 번에 하나만 올린다).

입력: 골든셋 C-5 항목의 고객 발화 36건 + AI Hub 민원 QA(다산) 고객 발화에서 시드 20261015 로 뽑은 500건.
콜드 = 모델 적재(생성자 — 예열 포함) 시간 + 첫 mask() 호출. 웜 = 그 뒤 전체 입력 1회씩.

  .venv/bin/python eval/review-2026-10/masking_latency.py rule|old|klue
"""
import glob, json, random, statistics, sys, time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai")]
CONFIGS = {"rule": None, "old": ROOT / "models/koelectra-ner", "klue": ROOT / "models/korean-pii-ner-v3"}


def inputs():
    from evaluation.golden_set import load_golden_set
    gold = [it.customer_utterance for it in load_golden_set() if it.module == "C-5" and it.customer_utterance]
    rows = []
    for f in sorted(glob.glob(str(ROOT / "data/raw/aihub-minwon-qa/validation/label/다산콜센터/*.json"))):
        rows += json.load(open(f, encoding="utf-8"))
    texts = [(r.get("고객질문(요청)") or r.get("고객답변") or "").strip() for r in rows if r.get("화자") != "상담사"]
    texts = [t for t in texts if t]
    random.seed(20261015)
    return gold, random.sample(texts, 500)


def pct(xs, q):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


def main():
    name = sys.argv[1]
    import torch
    torch.set_num_threads(4)
    proc = psutil.Process(); rss = lambda: round(proc.memory_info().rss / 1e6)
    gold, aihub = inputs()
    from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter
    from provider import build_masking_provider
    before = rss()
    t0 = time.perf_counter()
    provider, ner_on = build_masking_provider(RuleMaskingAdapter(), ner_model_dir=CONFIGS[name])
    port = provider()
    load_ms = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter(); port.mask(gold[0]); first_ms = (time.perf_counter() - t1) * 1000
    after = rss()
    res = {"config": name, "ner_enabled": ner_on, "model_dir": str(CONFIGS[name]) if CONFIGS[name] else None,
           "rss_before_load_mb": before, "rss_after_load_mb": after, "rss_added_mb": after - before,
           "cold_load_ms": round(load_ms), "cold_first_mask_ms": round(first_ms, 1)}
    for label, xs in (("golden_c5", gold), ("aihub_500", aihub)):
        ts = []
        for t in xs:
            s = time.perf_counter(); port.mask(t); ts.append((time.perf_counter() - s) * 1000)
        res[label] = {"n": len(xs), "p50_ms": round(pct(ts, .5), 1), "p95_ms": round(pct(ts, .95), 1),
                      "max_ms": round(max(ts), 1), "mean_ms": round(statistics.mean(ts), 1),
                      "mean_chars": round(statistics.mean(len(t) for t in xs), 1)}
    res["rss_end_mb"] = rss()
    res["machine"] = "맥북 M5 CPU (torch 4 threads)"; res["date"] = "2026-10-15"
    print(json.dumps(res, ensure_ascii=False))
    out = ROOT / "eval/review-2026-10/results/masking_latency.json"
    prev = json.loads(out.read_text()) if out.exists() else {}
    prev[name] = res; out.write_text(json.dumps(prev, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
