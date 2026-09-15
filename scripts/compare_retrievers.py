#!/usr/bin/env python3
# Requirement: B-2, B-3, E-1
"""검색 방식 대조 — BM25 · 임베딩 · RRF 하이브리드 · 리랭킹을 **같은 골든셋·같은 커밋·같은 머신**에서 잰다.

`w4-dense-vector-index` · `w4-rrf-hybrid` · `w4-reranker` 의 표를 한 번에 낸다. 따로 재면 커밋·ES 상태·
장치가 조금씩 달라져 줄끼리 비교가 안 된다.

    export ELASTICSEARCH_URL=http://localhost:9200
    .venv/bin/python scripts/index_knowledge_base.py --to-es --recreate      # 본문 + 임베딩
    .venv/bin/python scripts/compare_retrievers.py                            # 전부
    .venv/bin/python scripts/compare_retrievers.py --only bm25,dense          # 일부

**채점은 하네스와 같은 함수다** — `evaluation.harness.retrieval_query`(맥락 + 발화)와
`evaluation.metrics.retrieval.aggregate_recall_mrr`. 여기서 산식을 새로 쓰지 않는다.

**지연은 `retrieve()` 한 번의 벽시계 시간**이다(질의 임베딩·ES·병합·리랭킹 포함, 발화 1건씩 순차).
예열 1회는 빼고 잰다. ⚠ **로컬 CPU 값이다** — 운영(g4dn T4, 런북 22장은 측정 인스턴스 분리를 요구한다)과 다르다.
p95 ≤1,000ms(4.1절) 대조는 «이 머신에서» 의 대조로만 읽는다.

⚠ **k 를 여러 값으로 재는 것은 고르기 위해서가 아니라 민감도를 보려는 것이다.** 표본 96건에서 가장 좋은 k 를
골라 기본값으로 박으면 골든셋에 맞춘 것이 된다. 결과는 전부 찍고, 기본값은 관례(60)에 둔다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]

from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from evaluation.metrics.latency import summarize_latency  # noqa: E402
from evaluation.metrics.retrieval import aggregate_recall_mrr, hit_at_k  # noqa: E402
from retrieval.adapter.outbound.cross_encoder_reranker import (  # noqa: E402
    BgeRerankerScorer,
    CrossEncoderReranker,
)
from retrieval.adapter.outbound.es_bm25_retriever import EsBm25Retriever  # noqa: E402
from retrieval.adapter.outbound.es_dense_retriever import EsDenseRetriever  # noqa: E402
from retrieval.adapter.outbound.es_index import SINGLE_INDEX  # noqa: E402
from retrieval.adapter.outbound.hybrid_retriever import HybridRetriever  # noqa: E402
from retrieval.adapter.outbound.koe5_embedder import KoE5Embedder  # noqa: E402


def git_commit() -> str:
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip() or "?"
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                           capture_output=True, text=True).stdout.strip()
    return f"{head}-dirty" if dirty else head


def measure(retriever, items, *, top_k: int = 5) -> dict:
    queries = [retrieval_query(it) for it in items]
    asyncio.run(retriever.retrieve(queries[0], top_k=top_k))  # 예열 — 첫 호출의 모델·연결 준비를 빼고 잰다
    pairs, latencies, missed = [], [], []
    for it, q in zip(items, queries):
        t0 = time.perf_counter()
        docs = asyncio.run(retriever.retrieve(q, top_k=top_k))
        latencies.append((time.perf_counter() - t0) * 1000)
        got = [d.doc_id for d in docs]
        pairs.append((it.expected_doc_ids, got))
        if not hit_at_k(it.expected_doc_ids, got, k=top_k):
            missed.append(it.id)
    scores = aggregate_recall_mrr(pairs)
    lat = summarize_latency(latencies)
    return {
        "recall_at_5": scores["recall_at_k"],
        "mrr": scores["mrr"],
        "hits": len(items) - len(missed),
        "n": scores["n"],
        "p50_ms": lat["p50"],
        "p95_ms": lat["p95"],
        "missed": missed,
        "top1": sum(1 for exp, got in pairs if got and got[0] in exp),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden-set", type=Path, default=ROOT / "golden-set" / "v1-150.json")
    ap.add_argument("--index", default=SINGLE_INDEX)
    ap.add_argument("--embed-model", type=Path, default=ROOT / "models" / "koe5")
    ap.add_argument("--rerank-model", type=Path, default=ROOT / "models" / "bge-reranker-v2-m3")
    ap.add_argument("--device", default=None, help="cpu(기본) · mps · cuda")
    ap.add_argument("--only", default=None, help="쉼표로 구분한 변형 이름 접두어")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    from elasticsearch import Elasticsearch

    client = Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))
    items = [it for it in load_golden_set(args.golden_set) if it.module == "B"]

    bm25 = EsBm25Retriever(client, index=args.index)
    embedder = KoE5Embedder(args.embed_model, device=args.device)
    dense = EsDenseRetriever(client, embedder, index=args.index)

    variants: list[tuple[str, callable]] = [
        ("bm25", lambda: bm25),
        ("dense", lambda: dense),
    ]
    for k in (10, 30, 60, 100):
        variants.append((f"hybrid k={k} cand=20", lambda k=k: HybridRetriever([bm25, dense], k=k, candidates=20)))

    scorer_box: list[BgeRerankerScorer] = []

    def scorer():
        if not scorer_box:
            scorer_box.append(BgeRerankerScorer(args.rerank_model, device=args.device))
        return scorer_box[0]

    hybrid60 = HybridRetriever([bm25, dense], k=60, candidates=20)
    variants += [
        ("rerank(bm25) cand=5", lambda: CrossEncoderReranker(bm25, scorer(), candidates=5)),
        ("rerank(bm25) cand=20", lambda: CrossEncoderReranker(bm25, scorer(), candidates=20)),
        ("rerank(dense) cand=5", lambda: CrossEncoderReranker(dense, scorer(), candidates=5)),
        ("rerank(dense) cand=20", lambda: CrossEncoderReranker(dense, scorer(), candidates=20)),
        ("rerank(hybrid k=60) cand=5", lambda: CrossEncoderReranker(hybrid60, scorer(), candidates=5)),
        ("rerank(hybrid k=60) cand=20", lambda: CrossEncoderReranker(hybrid60, scorer(), candidates=20)),
    ]
    if args.only:
        wanted = [w.strip() for w in args.only.split(",")]
        variants = [v for v in variants if any(v[0].startswith(w) for w in wanted)]

    meta = {
        "date": str(date.today()),
        "commit": git_commit(),
        "golden_set": args.golden_set.name,
        "index": args.index,
        "embed_model": args.embed_model.name,
        "rerank_model": args.rerank_model.name,
        "device": embedder.device,
        "machine": f"{platform.system()} {platform.machine()}",
        "command": "scripts/compare_retrievers.py " + " ".join(sys.argv[1:]),
    }
    print(" · ".join(f"{k} {v}" for k, v in meta.items()))
    print(f"{'변형':32} {'Recall@5':>9} {'hits':>7} {'MRR':>7} {'top1':>5} {'p50ms':>7} {'p95ms':>7}")

    results = {}
    for name, build in variants:
        r = measure(build(), items)
        results[name] = r
        print(f"{name:32} {r['recall_at_5']:9.3f} {r['hits']:>3}/{r['n']:<3} {r['mrr']:7.3f} "
              f"{r['top1']:>5} {r['p50_ms']:7.0f} {r['p95_ms']:7.0f}")

    out = args.out or ROOT / "data" / "processed" / "retrieval-compare" / f"{meta['date']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=2) + "\n")
    print(f"\n저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
