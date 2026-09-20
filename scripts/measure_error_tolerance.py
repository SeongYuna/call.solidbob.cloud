#!/usr/bin/env python3
# Requirement: E-3, B-2, C-5
"""STT 오류 내성 곡선 — 오류율 0·5·10·15·20% 에서 검색 품질과 C-5 누락을 잰다 ([4.2절](/docs/04/)).

    export ELASTICSEARCH_URL=http://localhost:9200
    .venv/bin/python scripts/index_knowledge_base.py --to-es --recreate   # 임베딩 포함
    .venv/bin/python scripts/measure_error_tolerance.py --device mps
    .venv/bin/python scripts/measure_error_tolerance.py --only masking

`w5-error-tolerance-curve`(검색) · `w5-masking-recall-curve`(C-5) 두 티켓의 표를 낸다.

## 무엇에 오류를 넣는가

- **검색** — 하네스가 실제로 검색에 넣는 문자열(`retrieval_query` = 앞선 맥락 + 고객 발화), B 항목 96건
- **C-5** — 골든셋 **고객 발화 전부**(개인정보 유무 무관)를 한 말뭉치로 주입한 뒤 개인정보 항목만 채점한다.
  09-14 캘리브레이션(고객 발화 136건·시드 20260914)과 같은 말뭉치다

x 축은 목표값이 아니라 **주입 후 실제로 잰 WER** 이다(`InjectionResult.actual_wer`). 목표 수치(오류 10% ≥0.60)는
판정선으로만 대조하고 코드에 넣지 않는다.

## 시드 여러 개 → 최저치

같은 오류율이라도 어느 단어가 깨지느냐에 따라 값이 흔들린다. 시드 3개로 재고 **점마다 최저치**를 곡선으로 쓴다
(절대 원칙 4). 시드별 값도 JSON 에 남긴다.

## 이 곡선이 말하지 않는 것

주입기는 실측 편집 81건 중 **46.9%(환청·의미 붕괴)를 흉내 내지 못한다**(`error_injection/profile.py`). 같은 WER 에서
실제 STT 보다 덜 파괴적이므로 **곡선은 낙관 쪽으로 기운다.** 이 문장 없이 숫자만 옮기지 않는다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai")]

from evaluation.error_injection.injector import inject  # noqa: E402
from evaluation.error_injection.profile import UNMODELED_SHARE  # noqa: E402
from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from evaluation.metrics import masking_robustness  # noqa: E402
from evaluation.metrics.retrieval import aggregate_recall_mrr  # noqa: E402

LEVELS = (0.0, 0.05, 0.10, 0.15, 0.20)
SEEDS = (20260914, 20260915, 20260916)


def commit() -> str:
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    return head + ("-dirty" if dirty else "")


def retrieval_curve(items, retrievers, seeds) -> dict:
    b_items = [it for it in items if it.module == "B"]
    queries = [retrieval_query(it) for it in b_items]
    out: dict = {}
    for name, r in retrievers.items():
        asyncio.run(r.retrieve(queries[0], top_k=5))  # 예열
        rows = []
        for level in LEVELS:
            per_seed = []
            for seed in seeds:
                inj = inject(queries, level, seed=seed)
                pairs = [
                    (it.expected_doc_ids, [d.doc_id for d in asyncio.run(r.retrieve(q, top_k=5))])
                    for it, q in zip(b_items, inj.texts)
                ]
                s = aggregate_recall_mrr(pairs)
                per_seed.append({"seed": seed, "actual_wer": inj.actual_wer, "reached": inj.reached,
                                 "recall_at_5": s["recall_at_k"], "mrr": s["mrr"],
                                 "hits": round(s["recall_at_k"] * s["n"]), "n": s["n"]})
                if level == 0.0:
                    break  # 0% 는 시드와 무관하게 원문 그대로다
            worst = min(per_seed, key=lambda x: x["recall_at_5"])
            rows.append({"target": level, "per_seed": per_seed,
                         "min_recall_at_5": worst["recall_at_5"], "min_hits": worst["hits"],
                         "min_mrr": min(x["mrr"] for x in per_seed),
                         "wer_range": [min(x["actual_wer"] for x in per_seed), max(x["actual_wer"] for x in per_seed)]})
            print(f"  {name:14} 목표 {level:.2f} · 실제 WER {rows[-1]['wer_range'][0]:.3f}~{rows[-1]['wer_range'][1]:.3f} "
                  f"· Recall@5 최저 {worst['recall_at_5']:.3f} ({worst['hits']}/{worst['n']}) · MRR 최저 {rows[-1]['min_mrr']:.3f}")
        out[name] = rows
    return out


def masking_curve(items, maskers, seeds) -> dict:
    corpus_items = [it for it in items if it.customer_utterance]
    texts = [it.customer_utterance for it in corpus_items]
    out: dict = {}
    for name, masker in maskers.items():
        rows = []
        for level in LEVELS:
            per_seed = []
            for seed in seeds:
                inj = inject(texts, level, seed=seed)
                cases = []
                negatives_hit = 0
                negatives = 0
                for it, injected in zip(corpus_items, inj.texts):
                    if not it.pii_patterns:
                        continue
                    masked, spans = masker.mask(injected)
                    for p in it.pii_patterns:
                        if p.masked_expected and p.raw_span:
                            cases.append(masking_robustness.classify(it.id, p.pattern, p.raw_span, injected, masked))
                        elif not p.masked_expected:
                            negatives += 1
                            negatives_hit += int(p.pattern in {s.type for s in spans})
                sc = masking_robustness.score(cases)
                per_seed.append({"seed": seed, "actual_wer": inj.actual_wer, **sc,
                                 "over_masked_negatives": negatives_hit, "negatives": negatives})
                if level == 0.0:
                    break
            worst = max(per_seed, key=lambda x: x["miss_count"])
            rows.append({"target": level, "per_seed": per_seed, "max_miss_count": worst["miss_count"],
                         "wer_range": [min(x["actual_wer"] for x in per_seed), max(x["actual_wer"] for x in per_seed)]})
            print(f"  {name:10} 목표 {level:.2f} · 실제 WER {rows[-1]['wer_range'][0]:.3f}~{rows[-1]['wer_range'][1]:.3f} "
                  f"· 누락 최대 {worst['miss_count']} (판정 {worst['judged']} · 소거 {worst['erased_count']}) "
                  f"{worst['missed_items']} · 음성 과잉 {worst['over_masked_negatives']}/{worst['negatives']}")
        out[name] = rows
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden-set", type=Path, default=ROOT / "golden-set" / "v1-150.json")
    ap.add_argument("--only", choices=("retrieval", "masking"), default=None)
    ap.add_argument("--device", default=None)
    ap.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    args = ap.parse_args()

    items = load_golden_set(args.golden_set)
    meta = {"date": str(date.today()), "commit": commit(), "golden_set": args.golden_set.name, "seeds": args.seeds,
            "levels": LEVELS, "unmodeled_share": UNMODELED_SHARE,
            "command": "scripts/measure_error_tolerance.py " + " ".join(sys.argv[1:])}
    print(" · ".join(f"{k} {v}" for k, v in meta.items()))
    result: dict = {"meta": meta}

    if args.only in (None, "retrieval"):
        from elasticsearch import Elasticsearch
        from provider import build_model_retriever
        from retrieval.adapter.outbound.es_bm25_retriever import EsBm25Retriever

        client = Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))
        retrievers = {"bm25": EsBm25Retriever(client)}
        # 모델 계열은 **모델 파일이 있을 때만** 잰다(2026-09-21). 전에는 없으면 통째로 멈춰, 모델이 없는 머신에서는
        # 운영 구성(BM25)의 곡선조차 못 냈다. 빠진 계열은 조용히 넘기지 않고 `meta.skipped` 와 화면에 남긴다 —
        # 그림에 계열이 없는 이유가 「안 쟀다」인지 「잴 수 없었다」인지 뒤에서 구분할 수 있어야 한다.
        if (ROOT / "models" / "koe5").is_dir():
            dense, l1 = build_model_retriever(client, embed_model_dir=ROOT / "models" / "koe5", device=args.device)
            if l1[:1] != ["retrieval_dense"]:
                raise SystemExit(f"모델 검색을 못 띄웠다: {l1}")
            retrievers["dense"] = dense
            if (ROOT / "models" / "bge-reranker-v2-m3").is_dir():
                rerank, l2 = build_model_retriever(client, embed_model_dir=ROOT / "models" / "koe5",
                                                   rerank_model_dir=ROOT / "models" / "bge-reranker-v2-m3", device=args.device)
                if l2[:2] != ["retrieval_dense", "rerank"]:
                    raise SystemExit(f"리랭커를 못 띄웠다: {l2}")
                retrievers["rerank-dense"] = rerank
            else:
                meta.setdefault("skipped", []).append("rerank-dense — models/bge-reranker-v2-m3 없음")
        else:
            meta.setdefault("skipped", []).append("dense · rerank-dense — models/koe5 없음")
        meta["device"] = args.device or "cpu"
        print("\n[검색]" + (f"  ⚠ 건너뜀: {meta['skipped']}" if meta.get("skipped") else ""))
        result["retrieval"] = retrieval_curve(items, retrievers, args.seeds)

    if args.only in (None, "masking"):
        from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter

        print("\n[C-5 마스킹]")
        maskers = {"rule": RuleMaskingAdapter()}
        if (ROOT / "models" / "koelectra-ner").is_dir():
            # torch 를 끌어오는 import 라 모델이 있을 때만 한다 — 없는 머신에서도 규칙 곡선은 나와야 한다
            from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger
            from pii_ner.adapter.outbound.layered_masking_adapter import LayeredMaskingAdapter

            maskers["rule+ner"] = LayeredMaskingAdapter(RuleMaskingAdapter(), KoElectraNerTagger(ROOT / "models" / "koelectra-ner"))
        else:
            meta.setdefault("skipped", []).append("rule+ner — models/koelectra-ner 없음")
            print("  ⚠ 건너뜀: rule+ner — models/koelectra-ner 없음")
        result["masking"] = masking_curve(items, maskers, args.seeds)

    out = ROOT / "data" / "processed" / "error-tolerance" / f"{meta['date']}-{args.only or 'all'}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n")
    print(f"\n저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
