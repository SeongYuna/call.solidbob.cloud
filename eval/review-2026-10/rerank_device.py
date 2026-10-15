# Requirement: B-3, E-1
"""리랭커(bge-reranker-v2-m3) 지연을 **장치별로** 잰다 — CPU vs 맥북 GPU(MPS). 집 PC(GPU) 대신 오늘 할 수 있는 GPU 측정.

후보: KoE5 dense(운영 구성)를 **메모리 안 코사인**으로 102문항 상위 20 — compare_embedders.py 와 같은 방식(ES 를 띄우지 않는다).
  KoE5 는 후보를 만든 뒤 내린다(모델 한 번에 하나). 리랭커 입력은 조항 제목+본문(`embedding_input`) — ES 색인 결과의 snippet 이 아니라서
  `rerank_r1~3`(ES 경유) 값과 1~2문항 다를 수 있다. 장치끼리의 비교는 같은 후보·같은 입력이다.
채점: evaluation.metrics.retrieval(규칙). 지연 = 질의 1건의 리랭커 score() 호출 시간(후보 생성 제외).

  .venv/bin/python eval/review-2026-10/rerank_device.py mps 3     # 장치 · 반복 횟수
"""
import gc, json, statistics, sys, time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai"), str(Path(__file__).parent)]
from compare_embedders import MODELS, embed  # noqa: E402
from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from evaluation.metrics.retrieval import aggregate_recall_mrr  # noqa: E402
from retrieval.adapter.outbound.cross_encoder_reranker import BgeRerankerScorer  # noqa: E402
from retrieval.adapter.outbound.es_index import embedding_input  # noqa: E402
from retrieval.adapter.outbound.knowledge_base_loader import load_chunks  # noqa: E402
from transformers import AutoModel, AutoTokenizer  # noqa: E402


def pct(xs, q):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


def main():
    device, reps = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1
    chunks = load_chunks(ROOT / "knowledge-base"); ids = [c.doc_id for c in chunks]; texts = [embedding_input(c) for c in chunks]
    items = [it for it in load_golden_set() if it.module == "B" and it.expected_doc_ids]
    queries = [retrieval_query(it) for it in items]
    path, qp, pp, pooling, ml = MODELS["KoE5 (운영)"]
    tok = AutoTokenizer.from_pretrained(path); model = AutoModel.from_pretrained(path).eval()
    P = embed(tok, model, [pp + t for t in texts], pooling, ml); Q = embed(tok, model, [qp + q for q in queries], pooling, ml)
    cand = (Q @ P.T).topk(20, dim=1).indices.tolist()
    del model, tok, P, Q; gc.collect()

    gold = [it.expected_doc_ids for it in items]
    base = aggregate_recall_mrr(list(zip(gold, [[ids[j] for j in c[:5]] for c in cand])), k=5)
    scorer = BgeRerankerScorer(ROOT / "models/bge-reranker-v2-m3", device=device)
    scorer.score(queries[0], [texts[j] for j in cand[0][:5]])  # 예열
    out = {"device": device, "reps": reps, "n": len(items), "date": "2026-10-15", "machine": "맥북 M5 (GPU 10코어 · MPS)" if device == "mps" else "맥북 M5 CPU",
           "dense_only": {"recall_at_5": round(base["recall_at_k"], 3), "mrr": round(base["mrr"], 3)}}
    for k in (5, 20):
        lat, got = [], None
        for _ in range(reps):
            g = []
            for q, c in zip(queries, cand):
                s = time.perf_counter(); sc = scorer.score(q, [texts[j] for j in c[:k]])
                if device == "mps": torch.mps.synchronize()
                lat.append((time.perf_counter() - s) * 1000)
                order = sorted(range(k), key=lambda i: -sc[i]); g.append([ids[c[i]] for i in order[:5]])
            got = g
        agg = aggregate_recall_mrr(list(zip(gold, got)), k=5)
        out[f"k={k}"] = {"recall_at_5": round(agg["recall_at_k"], 3), "hits": round(agg["recall_at_k"] * len(items)), "mrr": round(agg["mrr"], 3),
                         "p50_ms": round(pct(lat, .5)), "p95_ms": round(pct(lat, .95)), "max_ms": round(max(lat)), "mean_ms": round(statistics.mean(lat)),
                         "samples": len(lat)}
        print(device, k, json.dumps(out[f"k={k}"], ensure_ascii=False), flush=True)
    res = ROOT / "eval/review-2026-10/results/rerank_device.json"
    prev = json.loads(res.read_text()) if res.exists() else {}
    prev[device] = out; res.write_text(json.dumps(prev, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
