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

**항목별 상위 k 도 남긴다**(2026-09-22, `w6-golden-set-loose-ends` ③). 집계 파일(`<날짜>.json`)은 그대로 두고
옆에 `<같은 이름>.items.json` 을 하나 더 쓴다 — 변형마다 항목마다 질의·정답·실제 상위 k(doc_id·score)·
첫 정답 순위. 전에는 `missed` 목록만 남아 **왜 틀렸는지 알려면 다시 돌려야 했다**(GS-205 가 그 경우였다).
⚠ 남기는 것은 **채점한 그 상위 k 뿐**이다 — 정답이 k 밖이면 `first_hit_rank` 는 `null` 이고, 몇 위였는지는
이 파일로 알 수 없다. 깊이를 늘려 따로 조회하면 지연 측정이 달라지므로 여기서 하지 않는다.

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


def item_row(item, query: str, docs, *, top_k: int = 5) -> dict:
    """항목 하나의 채점 근거 — 집계만으로는 «왜 틀렸나» 를 볼 수 없어서 남긴다.

    `first_hit_rank` 는 1부터 센 첫 정답 순위이고, 상위 k 안에 정답이 없으면 `None` 이다.
    `hit` 은 채점과 같은 함수(`hit_at_k`)로 낸다 — 여기서 판정을 따로 쓰면 집계와 어긋날 수 있다.
    """
    got = [d.doc_id for d in docs]
    expected = list(item.expected_doc_ids)
    first = next((i for i, did in enumerate(got[:top_k], 1) if did in expected), None)
    return {
        "id": item.id,
        "query": query,
        "expected": expected,
        "distractors": list(item.distractor_doc_ids),
        "hit": hit_at_k(item.expected_doc_ids, got, k=top_k),
        "first_hit_rank": first,
        "top_k": [
            {"rank": i, "doc_id": d.doc_id, "title": d.title, "score": round(float(d.score), 6)}
            for i, d in enumerate(docs[:top_k], 1)
        ],
    }


def items_path(out: Path) -> Path:
    """집계 파일 옆의 항목별 파일 경로 — `2026-09-22.json` → `2026-09-22.items.json`."""
    return out.with_name(f"{out.stem}.items{out.suffix}")


def measure(retriever, items, *, top_k: int = 5, rows: list | None = None) -> dict:
    """집계를 돌려준다. `rows` 를 주면 항목별 상위 k(`item_row`)를 거기 채운다 — 집계 형식은 바꾸지 않는다."""
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
        if rows is not None:
            rows.append(item_row(it, q, docs, top_k=top_k))
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

    results, per_item = {}, {}
    for name, build in variants:
        per_item[name] = []
        r = measure(build(), items, rows=per_item[name])
        results[name] = r
        print(f"{name:32} {r['recall_at_5']:9.3f} {r['hits']:>3}/{r['n']:<3} {r['mrr']:7.3f} "
              f"{r['top1']:>5} {r['p50_ms']:7.0f} {r['p95_ms']:7.0f}")

    out = args.out or ROOT / "data" / "processed" / "retrieval-compare" / f"{meta['date']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=2) + "\n")
    items_out = items_path(out)
    items_out.write_text(json.dumps({"meta": meta, "items": per_item}, ensure_ascii=False, indent=2) + "\n")
    print(f"\n저장: {out}")
    print(f"항목별 상위 k: {items_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
