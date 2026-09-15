#!/usr/bin/env python3
# Requirement: B-2, E-1
"""청킹 전략 3종 대조 — 「1 조항 = 1 청크」 · 고정 길이 · 시멘틱 (`w4-chunking-compare`).

    export ELASTICSEARCH_URL=http://localhost:9200
    .venv/bin/python scripts/compare_chunking.py

전략마다 **실험 인덱스를 따로** 적재한다(`cgexp-chunk-*` — 운영 레이아웃 이름과 섞이지 않게).
검색은 BM25·dense 두 가지로, 채점은 두 벌이다:

- **엄격** — 청크의 대표 조항 ID(글자를 가장 많이 차지한 조항)로 하네스와 똑같이 채점. 운영에 쓸 수 있는 값
- **느슨** — 청크가 덮은 조항 중 하나라도 정답이면 적중. **운영에서는 못 쓰는 값이다**(화면에 조항 하나를 띄워야 한다).
  엄격과의 차이가 «대표 ID 규칙 때문에 잃은 몫» 이다

⚠ 파일(TERM·MANUAL·POLICY) 경계는 넘지 않는다 — 한 파일 안의 조항만 이어 붙여 자른다.
⚠ 고정 길이 200/50 · 시멘틱 percentile 90 은 **골든셋으로 고르지 않은 값이다.**
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import date
from itertools import groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]

from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from evaluation.metrics.retrieval import aggregate_recall_mrr  # noqa: E402
from retrieval.adapter.outbound import es_index  # noqa: E402
from retrieval.adapter.outbound.es_bm25_retriever import SEARCH_FIELDS, EsBm25Retriever  # noqa: E402
from retrieval.adapter.outbound.es_dense_retriever import EsDenseRetriever  # noqa: E402
from retrieval.adapter.outbound.knowledge_base_loader import load_chunks  # noqa: E402
from retrieval.adapter.outbound.koe5_embedder import KoE5Embedder  # noqa: E402
from retrieval.domain.services.chunking_strategies import (  # noqa: E402
    article_stream_chunks,
    fixed_length_chunks,
    semantic_chunks,
    semantic_sentences,
)


def build_strategies(articles, embedder, *, size, overlap, percentile):
    groups = [list(g) for _, g in groupby(articles, key=lambda a: a.doc_type)]
    fixed, semantic = [], []
    for g in groups:
        tag = g[0].doc_type
        fixed += fixed_length_chunks(g, size=size, overlap=overlap, prefix=f"FIXED-{tag}")
        sentences = semantic_sentences(g)
        vectors = embedder.embed_passages(sentences)
        semantic += semantic_chunks(g, vectors, percentile=percentile, prefix=f"SEMANTIC-{tag}")
    return {
        "article": article_stream_chunks(articles),
        f"fixed {size}/{overlap}": fixed,
        f"semantic p{percentile:g}": semantic,
    }


def lenient_ids(client, index, body, covered_by_chunk, top_k=5):
    """collapse 없이 청크 순위를 받아 덮은 조항으로 풀어 앞에서부터 top_k 개(중복 제거)."""
    resp = client.search(index=index, size=50, source_excludes=[es_index.EMBEDDING_FIELD], **body)
    out: list[str] = []
    for h in resp["hits"]["hits"]:
        for d in covered_by_chunk[h["_id"]]:
            if d not in out:
                out.append(d)
    return out[:top_k]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden-set", type=Path, default=ROOT / "golden-set" / "v1-150.json")
    ap.add_argument("--embed-model", type=Path, default=ROOT / "models" / "koe5")
    ap.add_argument("--device", default=None)
    ap.add_argument("--size", type=int, default=200)
    ap.add_argument("--overlap", type=int, default=50)
    ap.add_argument("--percentile", type=float, default=90.0)
    args = ap.parse_args()

    from elasticsearch import Elasticsearch

    client = Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))
    items = [it for it in load_golden_set(args.golden_set) if it.module == "B"]
    articles = load_chunks(ROOT / "knowledge-base")
    embedder = KoE5Embedder(args.embed_model, device=args.device)
    strategies = build_strategies(articles, embedder, size=args.size, overlap=args.overlap, percentile=args.percentile)

    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    meta = {"date": str(date.today()), "commit": head + ("-dirty" if dirty else ""), "golden_set": args.golden_set.name,
            "n": len(items), "embed_model": args.embed_model.name, "device": embedder.device,
            "command": "scripts/compare_chunking.py " + " ".join(sys.argv[1:])}
    print(" · ".join(f"{k} {v}" for k, v in meta.items()))
    print(f"{'전략':18} {'청크':>4} {'평균자':>5} {'경계넘음':>6} │ {'검색':5} {'엄격 R@5':>8} {'hits':>6} {'MRR':>6} │ {'느슨 R@5':>8} {'hits':>6}")

    results = {}
    for name, stream in strategies.items():
        chunks = [s.chunk for s in stream]
        covered = {s.chunk.chunk_id: s.covered_doc_ids for s in stream}
        crossing = sum(1 for s in stream if len(s.covered_doc_ids) > 1)
        avg = sum(len(c.text) for c in chunks) / len(chunks)
        index = "cgexp-chunk-" + name.split()[0]
        vectors = embedder.embed_passages([es_index.embedding_input(c) for c in chunks])
        es_index.create_named_index(client, index, recreate=True, embedding_dims=es_index.EMBEDDING_DIMS)
        es_index.index_into(client, index, chunks, embeddings={c.chunk_id: v for c, v in zip(chunks, vectors)})

        retrievers = {"bm25": EsBm25Retriever(client, index=index), "dense": EsDenseRetriever(client, embedder, index=index)}
        results[name] = {"chunks": len(chunks), "avg_chars": avg, "crossing": crossing}
        for rname, r in retrievers.items():
            strict_pairs, lenient_pairs = [], []
            for it in items:
                q = retrieval_query(it)
                got = [d.doc_id for d in asyncio.run(r.retrieve(q, top_k=5))]
                strict_pairs.append((it.expected_doc_ids, got))
                if rname == "bm25":
                    body = {"query": {"multi_match": {"query": q, "fields": list(SEARCH_FIELDS)}}}
                else:
                    body = {"knn": r.build_knn(embedder.embed_queries([q])[0], 50)}
                lenient_pairs.append((it.expected_doc_ids, lenient_ids(client, index, body, covered)))
            s, l = aggregate_recall_mrr(strict_pairs), aggregate_recall_mrr(lenient_pairs)
            sh = round(s["recall_at_k"] * s["n"]); lh = round(l["recall_at_k"] * l["n"])
            results[name][rname] = {"strict": s, "lenient": l}
            print(f"{name:18} {len(chunks):>4} {avg:>5.0f} {crossing:>6} │ {rname:5} {s['recall_at_k']:>8.3f} {sh:>3}/{s['n']:<2} "
                  f"{s['mrr']:>6.3f} │ {l['recall_at_k']:>8.3f} {lh:>3}/{l['n']:<2}")
        client.indices.delete(index=index, ignore_unavailable=True)

    out = ROOT / "data" / "processed" / "chunking-compare" / f"{meta['date']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=2, default=str) + "\n")
    print(f"\n저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
