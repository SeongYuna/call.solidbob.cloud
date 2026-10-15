# Requirement: B-2, E-3
"""심사 질문 15 — 실제 Google STT WER(한국인 자연 발화 8kHz 0.358, n 20 — data/processed/bandwidth-penalty/result.json)이
기존 곡선의 끝(0.20)보다 높다. 같은 주입기(evaluation.error_injection.inject)·같은 시드 3개·같은 채점으로 0.40 까지 넓혀 잰다.
검색은 compare_embedders.py 와 같은 메모리 안 코사인(운영 KoE5 값 0.971/0.875 를 그대로 재현한 방식). BM25 는 로컬 ES 색인이
4.23 추가 전 판이라 넣지 않는다.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai"), str(Path(__file__).parent)]
from transformers import AutoModel, AutoTokenizer  # noqa: E402
from compare_embedders import MODELS, embed  # noqa: E402
from evaluation.error_injection.injector import inject  # noqa: E402
from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from evaluation.metrics.retrieval import aggregate_recall_mrr  # noqa: E402
from retrieval.adapter.outbound.knowledge_base_loader import load_chunks  # noqa: E402
from retrieval.adapter.outbound.es_index import embedding_input  # noqa: E402

LEVELS = (0.0, 0.10, 0.20, 0.30, 0.36, 0.40)
SEEDS = (20260914, 20260915, 20260916)
chunks = load_chunks(ROOT / "knowledge-base"); ids = [c.doc_id for c in chunks]
items = [it for it in load_golden_set() if it.module == "B" and it.expected_doc_ids]
queries = [retrieval_query(it) for it in items]
res = {}
for name in sys.argv[1:] or ["KoE5 (운영)"]:
    path, qp, pp, pooling, ml = MODELS[name]
    tok = AutoTokenizer.from_pretrained(path); model = AutoModel.from_pretrained(path).eval()
    P = embed(tok, model, [pp + embedding_input(c) for c in chunks], pooling, ml)
    rows = []
    for lv in LEVELS:
        per = []
        for seed in SEEDS:
            inj = inject(queries, lv, seed=seed)
            Q = embed(tok, model, [qp + q for q in inj.texts], pooling, ml)
            got = [[ids[j] for j in r] for r in (Q @ P.T).topk(5, dim=1).indices.tolist()]
            s = aggregate_recall_mrr(list(zip([it.expected_doc_ids for it in items], got)))
            per.append({"seed": seed, "actual_wer": round(inj.actual_wer, 3), "reached": inj.reached,
                        "recall_at_5": s["recall_at_k"], "hits": round(s["recall_at_k"] * s["n"]), "mrr": s["mrr"]})
            if lv == 0.0: break
        w = min(per, key=lambda x: x["recall_at_5"])
        rows.append({"target": lv, "wer_range": [min(p["actual_wer"] for p in per), max(p["actual_wer"] for p in per)],
                     "min_recall_at_5": round(w["recall_at_5"], 3), "min_hits": w["hits"], "n": len(items),
                     "min_mrr": round(min(p["mrr"] for p in per), 3), "per_seed": per})
        print(name, lv, rows[-1]["wer_range"], rows[-1]["min_recall_at_5"], rows[-1]["min_hits"], rows[-1]["min_mrr"], flush=True)
    res[name] = rows
out = ROOT / "eval/review-2026-10/results/error_curve_extended.json"
prev = json.loads(out.read_text()) if out.exists() else {}
prev.update(res); out.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
