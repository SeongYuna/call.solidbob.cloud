#!/usr/bin/env python3
# Requirement: B-2
"""검색 캐시 측정 — 적중/미적중 지연 · 켠 값과 끈 값의 품질이 같은지 · 재적재 무효화 · 반복 질문 비율 (`w7-lru-cache`).

    export ELASTICSEARCH_URL=http://localhost:9200
    .venv/bin/python scripts/measure_cache.py --device mps [--check-reindex]

⚠ **운영 적중률은 잴 수 없다** — 운영 트래픽이 없다. 골든셋을 두 번 돌리는 것은 «적중하면 얼마나 빨라지나» 를 재는 것이지
적중률이 아니다. 대신 AI Hub 다산 실제 고객 질문에서 **정확히 같은 문장이 반복되는 비율**을 참고로 찍는다 —
STT 전사는 같은 뜻이라도 글자가 달라지므로 **이 비율은 실제 적중률의 상한에 가깝다고도 말할 수 없다**(띄어쓰기 하나로 키가 달라진다).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai")]

from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from evaluation.metrics.latency import summarize_latency  # noqa: E402
from evaluation.metrics.retrieval import aggregate_recall_mrr  # noqa: E402
from retrieval.adapter.outbound.cached_retriever import CachedRetriever, es_index_epoch  # noqa: E402
from retrieval.adapter.outbound.es_index import SINGLE_INDEX  # noqa: E402


def timed_pass(retriever, items):
    pairs, lat = [], []
    for it in items:
        t0 = time.perf_counter()
        docs = asyncio.run(retriever.retrieve(retrieval_query(it), top_k=5))
        lat.append((time.perf_counter() - t0) * 1000)
        pairs.append((it.expected_doc_ids, [d.doc_id for d in docs]))
    s = aggregate_recall_mrr(pairs)
    return {"recall_at_5": s["recall_at_k"], "mrr": s["mrr"], "latency_ms": summarize_latency(lat), "ids": [p[1] for p in pairs]}


def repeat_rate() -> dict:
    files = sorted((ROOT / "data" / "raw" / "aihub-minwon-qa" / "validation" / "label" / "다산콜센터").glob("*.json"))
    qs = []
    for f in files:
        for row in json.loads(f.read_text(encoding="utf-8")):
            q = (row.get("고객질문(요청)") or "").strip()
            if row.get("화자") == "고객" and q:
                qs.append(re.sub(r"\s+", " ", q))
    c = Counter(qs)
    repeated = sum(n - 1 for n in c.values() if n > 1)
    return {"questions": len(qs), "distinct": len(c), "repeat_share": repeated / len(qs) if qs else float("nan")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default=None)
    ap.add_argument("--check-reindex", action="store_true", help="--recreate 재적재 뒤 캐시가 비는지 실제로 본다 (인덱스를 다시 만든다)")
    args = ap.parse_args()

    from elasticsearch import Elasticsearch
    from provider import build_model_retriever

    client = Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))
    items = [it for it in load_golden_set(ROOT / "golden-set" / "v1-150.json") if it.module == "B"]
    base, layers = build_model_retriever(client, embed_model_dir=ROOT / "models" / "koe5",
                                         rerank_model_dir=ROOT / "models" / "bge-reranker-v2-m3", device=args.device, cache_size=0)
    asyncio.run(base.retrieve("예열", top_k=5))
    uncached = timed_pass(base, items)
    cached = CachedRetriever(base, epoch=es_index_epoch(client, SINGLE_INDEX), epoch_check_s=0)
    miss = timed_pass(cached, items)
    hit = timed_pass(cached, items)

    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"측정일 {date.today()} · 커밋 {head}-dirty · 골든셋 v1-150 B {len(items)}건 · 검색 {layers} · 장치 {args.device or 'cpu'}")
    for name, r in (("캐시 없음", uncached), ("캐시 1회차(미적중)", miss), ("캐시 2회차(적중)", hit)):
        lat = r["latency_ms"]
        print(f"  {name:18} Recall@5 {r['recall_at_5']:.3f} · MRR {r['mrr']:.3f} · p50 {lat['p50']:.1f}ms · p95 {lat['p95']:.1f}ms")
    same = uncached["ids"] == miss["ids"] == hit["ids"]
    print(f"  세 경우 상위 5 순위가 문항마다 같은가: {same}  · 캐시 통계 {cached.stats}")

    if args.check_reindex:
        before = len(cached._cache)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "index_knowledge_base.py"), "--to-es", "--recreate"],
                       check=True, capture_output=True, env={**os.environ})
        asyncio.run(cached.retrieve(retrieval_query(items[0]), top_k=5))
        print(f"  --recreate 재적재 뒤: 캐시 {before}건 → {len(cached._cache)}건 · 무효화 {cached.invalidations}회")

    print(f"  AI Hub 다산 고객 질문 반복: {repeat_rate()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
