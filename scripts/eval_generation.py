#!/usr/bin/env python3
# Requirement: B-4, B-5, B-6, E-2, COST-1
"""B-4 서류 목록 카드 — 환각·출처 표시율·지연·토큰을 골든셋으로 잰다.

    export ELASTICSEARCH_URL=http://localhost:9200
    .venv/bin/python scripts/eval_generation.py --no-schema                                  # kanana (decisions/207 기본)
    .venv/bin/python scripts/eval_generation.py --model hf.co/LGAI-EXAONE/EXAONE-4.0-1.2B-GGUF:latest            # EXAONE + 스키마
    .venv/bin/python scripts/eval_generation.py --model hf.co/LGAI-EXAONE/EXAONE-4.0-1.2B-GGUF:latest --no-schema  # 같은 조건 대조

`w6-card-generation`(지연) · `w6-hallucination-eval`(환각) · `w6-generation-model-compare`(대조) · `w7-token-cost`(토큰)
네 티켓의 수치를 한 번에 낸다. **같은 검색 결과를 두 모델에 넣도록** 검색 결과를 먼저 뽑아 파일에 고정한다(`--docs-cache`).

채점은 `evaluation.metrics.generation` — 생성기 필터와 **독립된** 규칙이다(자기 필터로 자기를 채점하지 않는다).

⚠ 골든셋 B 항목은 **96건**이다. 검수 기준 「150문항 중 5건 이하」의 150 에 못 미친다 — **환산하지 않고 96 기준으로 적는다.**
⚠ 로컬 Ollama(Apple Silicon Metal) 값이다. 운영 T4 와 다르다(런북 11·22장).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai")]

from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from evaluation.metrics.generation import card_hallucinations, raw_hallucinations, score_generation  # noqa: E402
from evaluation.metrics.latency import summarize_latency  # noqa: E402
from generation.adapter.outbound.document_list_card_adapter import DocumentListCardAdapter  # noqa: E402
from generation.adapter.outbound.ollama_chat import DEFAULT_MODEL, OllamaChat  # noqa: E402
from hub.app.dtos.retrieved_doc_dto import RetrievedDoc  # noqa: E402


def load_docs(items, cache: Path, retriever_kind: str, device: str | None) -> dict[str, list[dict]]:
    if cache.exists():
        return json.loads(cache.read_text())
    from elasticsearch import Elasticsearch
    from provider import build_model_retriever

    client = Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))
    rerank = ROOT / "models" / "bge-reranker-v2-m3" if retriever_kind == "rerank-dense" else None
    retriever, layers = build_model_retriever(client, embed_model_dir=ROOT / "models" / "koe5", rerank_model_dir=rerank, device=device)
    print(f"검색 구성 {retriever_kind} · 층 {layers}")
    out = {}
    for it in items:
        docs = asyncio.run(retriever.retrieve(retrieval_query(it), top_k=5))
        out[it.id] = [d.__dict__ for d in docs]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden-set", type=Path, default=ROOT / "golden-set" / "v1-150.json")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--ollama-url", default="http://localhost:11434")
    ap.add_argument("--top-n", type=int, default=1, help="카드를 생성할 상위 조항 수 (나머지는 스니펫)")
    ap.add_argument("--retriever", default="rerank-dense", choices=("dense", "rerank-dense"))
    ap.add_argument("--device", default="mps")
    ap.add_argument("--no-schema", action="store_true", help="JSON 스키마 강제 없이 (모델 대조 — kanana 는 스키마를 못 받는다)")
    ap.add_argument("--limit", type=int, default=None, help="앞에서 몇 문항만 (프롬프트 확인용 — 기록하지 않는다)")
    ap.add_argument("--docs-cache", type=Path, default=ROOT / "data" / "processed" / "generation-eval" / "docs-rerank-dense.json")
    args = ap.parse_args()

    items = [it for it in load_golden_set(args.golden_set) if it.module == "B"]
    docs_by_item = load_docs(items, args.docs_cache, args.retriever, args.device)
    if args.limit:
        items = items[: args.limit]
    chat = OllamaChat(args.ollama_url, model=args.model)
    adapter = DocumentListCardAdapter(chat, generate_top_n=args.top_n, use_schema=not args.no_schema)
    # 모델 적재를 빼고 잰다 — 다른 모델을 쓰고 난 직후면 Ollama 가 적재에 10초를 넘겨 첫 호출들이 타임아웃이 난다
    # (2026-09-15 첫 실행에서 앞 15건이 전부 그랬다). 성공할 때까지 예열한다.
    warm = RetrievedDoc(**docs_by_item[items[0].id][0])
    for _ in range(10):
        asyncio.run(adapter.to_cards("예열", [warm]))
        if adapter.last_details and adapter.last_details[0].outcome != "error":
            break

    rows, latencies, prompt_tokens, output_tokens, examples = [], [], [], [], []
    no_docs = 0
    for it in items:
        docs = [RetrievedDoc(**d) for d in docs_by_item[it.id]]
        if not docs:
            no_docs += 1
        cards = asyncio.run(adapter.to_cards(it.customer_utterance or retrieval_query(it), docs))
        for card, detail in zip(cards, adapter.last_details):
            doc = next(d for d in docs if d.doc_id == detail.doc_id)
            source_text = doc.snippet  # 본문만 — 조항 제목을 서류 이름으로 옮겨 적은 것은 환각으로 센다
            rows.append({"item": it.id, "doc_id": card.source.doc_id, "summary": card.summary, "source_text": source_text,
                         "raw_output": detail.raw_output, "outcome": detail.outcome,
                         "relevant": doc.doc_id in it.expected_doc_ids})
            latencies.append(detail.elapsed_ms)
            prompt_tokens.append(detail.prompt_tokens)
            output_tokens.append(detail.output_tokens)
            h = raw_hallucinations(detail.raw_output, source_text)
            if h and len(examples) < 8:
                examples.append({"item": it.id, "doc_id": doc.doc_id, "hallucinated": h, "shipped": card_hallucinations(card.summary, source_text)})

    s = score_generation(rows)
    lat = summarize_latency([x for x in latencies if x > 0]) if any(latencies) else {}
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    meta = {"date": str(date.today()), "commit": head + ("-dirty" if dirty else ""), "golden_set": args.golden_set.name,
            "questions": len(items), "model": args.model, "top_n": args.top_n, "retriever": args.retriever, "schema": not args.no_schema,
            "command": "scripts/eval_generation.py " + " ".join(sys.argv[1:])}
    summary = {**s, "no_docs_questions": no_docs,
               "relevant_generated_cards": sum(1 for r in rows if r["relevant"]),
               "latency_ms": lat, "prompt_tokens_mean": sum(prompt_tokens) / len(rows) if rows else 0,
               "output_tokens_mean": sum(output_tokens) / len(rows) if rows else 0,
               "prompt_tokens_max": max(prompt_tokens, default=0), "output_tokens_max": max(output_tokens, default=0)}
    print(" · ".join(f"{k} {v}" for k, v in meta.items()))
    for k, v in summary.items():
        print(f"  {k}: {v}")
    for e in examples:
        print(f"  예) {e}")
    out = ROOT / "data" / "processed" / "generation-eval" / f"{meta['date']}-{args.model.replace('/', '_').replace(':', '_')}{'-noschema' if args.no_schema else ''}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "summary": summary, "rows": rows}, ensure_ascii=False, indent=1))
    print(f"저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
