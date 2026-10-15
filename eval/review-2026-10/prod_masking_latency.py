# 운영 노드(c7i.2xlarge) · 운영 이미지 0.1.50 · 운영 모델 파일로 마스킹 단계 지연. 구성 하나 = 프로세스 하나.
import json, sys, time, statistics, resource
sys.path[:0] = ["/app/server/apps", "/app/ai/apps", "/app/ai"]
name, mdir = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
import torch
from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter
from provider import build_masking_provider
inp = json.load(open("/work/lat_inputs.json", encoding="utf-8"))
t0 = time.perf_counter(); p, on = build_masking_provider(RuleMaskingAdapter(), ner_model_dir=mdir); m = p(); load = (time.perf_counter() - t0) * 1000
t1 = time.perf_counter(); m.mask(inp["golden_c5"][0]); first = (time.perf_counter() - t1) * 1000
def pct(xs, q): xs = sorted(xs); return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]
res = {"config": name, "ner_enabled": on, "torch_threads": torch.get_num_threads(), "load_ms": round(load), "first_ms": round(first, 1)}
allt = []
for rep in range(3):
    for k in ("golden_c5", "golden_b", "scripts_customer"):
        ts = []
        for t in inp[k]:
            s = time.perf_counter(); m.mask(t); ts.append((time.perf_counter() - s) * 1000)
        res.setdefault(k, []).append({"n": len(ts), "p50": round(pct(ts, .5), 1), "p95": round(pct(ts, .95), 1), "max": round(max(ts), 1)})
        allt += ts
res["all_3reps"] = {"n": len(allt), "p50": round(pct(allt, .5), 1), "p95": round(pct(allt, .95), 1), "max": round(max(allt), 1), "mean": round(statistics.mean(allt), 1)}
res["maxrss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
print("RESULT " + json.dumps(res, ensure_ascii=False), flush=True)
