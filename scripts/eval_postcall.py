#!/usr/bin/env python3
# Requirement: D-1, D-2, E-1
"""통화 후 초안 측정 — D-2 유형 제안 정확도 · D-1 모델 요약 반려율·지연 (`w7-postcall-spoke`).

    export ELASTICSEARCH_URL=http://localhost:9200
    .venv/bin/python scripts/eval_postcall.py --device mps [--summary-sample 50]

**데이터**: AI Hub 「민원(콜센터) 질의응답」 validation · 다산콜센터 대화셋 전부. 대화셋마다 `카테고리` 라벨이 있어 **D-2 를 라벨과 대조**한다.
골든셋에는 D 케이스가 0건이다 — 이 데이터가 유일한 채점 재료다.

⚠ **누수 가능성**: 지식베이스 TERM 은 이 데이터셋의 **고객의도 체계를 따라** 팀이 썼다(TERM.md 머리말). 장 구성이 카테고리와 맞는 것은
그 때문이다 — 그래서 이 정확도는 «다산 민원을 이 체계로 가를 수 있는가» 이지 다른 콜센터로 옮겨 가는 값이 아니다.
⚠ 대화셋은 **텍스트**다(전사 오류 없음). D-1 요약의 **품질은 재지 않는다** — 정답 요약이 없다. 재는 것은 규칙 검사에 걸린 비율·지연뿐이다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai")]

from evaluation.metrics.latency import summarize_latency  # noqa: E402
from generation.adapter.outbound.ollama_chat import DEFAULT_MODEL, OllamaChat  # noqa: E402
from hub.app.dtos.transcript_dto import TranscriptEvent  # noqa: E402
from postcall.adapter.outbound.rule_postcall_adapter import RulePostcallAdapter  # noqa: E402
from postcall_summary.adapter.outbound.model_postcall_adapter import ModelPostcallAdapter  # noqa: E402
from postcall_summary.domain.services.rules import INQUIRY_TYPES  # noqa: E402


def load_dialogs() -> list[tuple[str, str, list[TranscriptEvent]]]:
    by_id: dict[str, list[dict]] = defaultdict(list)
    for f in sorted((ROOT / "data" / "raw" / "aihub-minwon-qa" / "validation" / "label" / "다산콜센터").glob("*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            by_id[r["대화셋일련번호"]].append(r)
    out = []
    for did, rows in sorted(by_id.items()):
        rows.sort(key=lambda r: int(r["문장번호"]))
        segs = []
        for r in rows:
            spk = "customer" if r["화자"] == "고객" else "agent"
            text = (r.get("고객질문(요청)") or r.get("고객답변") or r.get("상담사답변") or r.get("상담사질문(요청)") or "").strip()
            if text:
                segs.append(TranscriptEvent(call_id=did, segment_id=int(r["문장번호"]), speaker=spk, text=text, is_final=True))
        out.append((did, rows[0]["카테고리"], segs))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default=None)
    ap.add_argument("--summary-sample", type=int, default=50)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    from elasticsearch import Elasticsearch
    from provider import build_model_retriever
    from retrieval.adapter.outbound.es_bm25_retriever import EsBm25Retriever

    client = Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))
    dialogs = load_dialogs()
    rerank, layers = build_model_retriever(client, embed_model_dir=ROOT / "models" / "koe5",
                                           rerank_model_dir=ROOT / "models" / "bge-reranker-v2-m3", device=args.device)
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"측정일 {date.today()} · 커밋 {head}-dirty · AI Hub 다산 validation 대화셋 {len(dialogs)}개 · 라벨 분포 {dict(Counter(c for _, c, _ in dialogs))}")

    for name, retr in (("bm25", EsBm25Retriever(client)), (f"dense+rerank {layers}", rerank)):
        adapter = ModelPostcallAdapter(RulePostcallAdapter(), chat=None, retrieval=retr)
        confusion: dict[str, Counter] = defaultdict(Counter)
        correct = none = 0
        for did, label, segs in dialogs:
            d = asyncio.run(adapter.summarize(did, segs))
            confusion[label][d.inquiry_type or "None"] += 1
            correct += int(d.inquiry_type == label)
            none += int(d.inquiry_type is None)
        print(f"\n[D-2 {name}] 정확도 {correct / len(dialogs):.3f} ({correct}/{len(dialogs)}) · 제안 없음 {none}")
        for label in INQUIRY_TYPES:
            row = confusion[label]
            n = sum(row.values())
            print(f"  {label:12} n={n:4}  맞음 {row[label]:4} ({row[label] / n:.3f})  {dict(row.most_common())}")

    rng = random.Random(20260915)
    sample = rng.sample(dialogs, min(args.summary_sample, len(dialogs)))
    chat = OllamaChat(model=args.model, num_predict=160, timeout_s=30)
    adapter = ModelPostcallAdapter(RulePostcallAdapter(), chat=chat, retrieval=None)
    asyncio.run(adapter.summarize("예열", sample[0][2]))
    sources, problems, lat, examples = Counter(), Counter(), [], []
    for did, label, segs in sample:
        d = asyncio.run(adapter.summarize(did, segs))
        det = adapter.last_detail
        sources[det.summary_source] += 1
        for p in det.problems:
            problems[p.split(" ")[0] + " " + p.split(" ")[1] if " " in p else p] += 1
        if det.elapsed_ms:
            lat.append(det.elapsed_ms)
        if len(examples) < 3:
            examples.append((label, d.summary_text[:160], det.problems[:2]))
    print(f"\n[D-1 {args.model}] 표본 {len(sample)}(시드 20260915) · 화면에 모델 요약 {sources['model']} · 규칙 발췌로 반려 {sources['rule']}")
    print(f"  반려 사유 {dict(problems)} · 지연 {summarize_latency(lat) if lat else '없음'}")
    for e in examples:
        print(f"  예) {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
