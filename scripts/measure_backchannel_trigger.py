#!/usr/bin/env python3
# Requirement: B-1, B-6
"""맞장구 억제 규칙(`decisions/216`) 1회 측정 — 대화체 보류 표본의 고객 턴마다 트리거 판정을 규칙 없이/함께 낸다.

    ELASTICSEARCH_URL=http://127.0.0.1:9200 .venv/bin/python scripts/measure_backchannel_trigger.py --device mps \\
        --e2e-texts data/processed/qa-2026-09-22/v2/dense-scores-1510.json \\
        --out jekyll/assets/backchannel-trigger-2026-09-22.json

**채택 규칙은 `decisions/216` 「사전 등록」에 적힌 것을 그대로 기계적으로 적용한다** — 여기서 값을 고르지 않는다(숫자 손잡이가 없다).

- 입력 글: 09-22 E2E 에서 서버가 받은 글(`--e2e-texts` 의 `text`, C-5 마스킹을 거친 것)을 `sid`·`seg` 로 대본 턴에 맞춘다. 없으면 대본 원문.
- 「규칙 없이 top-5」: 로컬 `callguard-kb-single`(읽기만) · KoE5 dense(리랭커 없음 · 215 문턱 꺼짐 — 운영 구성).
- (A) 위험 집합 = `needed` ∪ 「top-5 에 대본 절차 문서가 든 턴」 — 규칙이 발동을 끈 턴이 0 이어야 한다.
- (B) `backchannel` 중 규칙이 발동을 끈 비율 ≥ 0.90.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "scripts")]

from hub.app.dtos.transcript_dto import TranscriptEvent  # noqa: E402
from retrieval.adapter.outbound.is_final_trigger import IsFinalTrigger  # noqa: E402
from run_eval import _es_client, _git_commit, build_retriever  # noqa: E402

LABELS = ROOT / "golden-set" / "b6-conversational-2026-09-22.json"
B_MIN = 0.90  # decisions/216 사전 등록값


def _event(item: dict, text: str) -> TranscriptEvent:
    return TranscriptEvent(call_id=item["script"], segment_id=item["seq"], speaker="customer",
                           text=text, is_final=True, utterance_end_ms=None)


async def _run(args) -> dict:
    labels = json.loads(LABELS.read_text())
    e2e = {}
    if args.e2e_texts and args.e2e_texts.exists():
        for r in json.loads(args.e2e_texts.read_text()):
            e2e[(r["sid"], int(r["seg"]))] = r["text"]

    off = IsFinalTrigger(suppress_backchannel=False)
    on = IsFinalTrigger(suppress_backchannel=True)
    port = None
    if not args.no_retrieval:
        client = _es_client(os.environ.get("ELASTICSEARCH_URL"))
        if client is None:
            raise SystemExit("ELASTICSEARCH_URL 이 없다 — --no-retrieval 로 돌리거나 로컬 ES 를 준다")
        port = build_retriever(client, index=args.index, kind="dense", device=args.device, no_answer_abstain=False)

    rows = []
    for it in labels["items"]:
        text = e2e.get((it["script"], it["seq"]))
        text_src = "e2e" if text is not None else "script"
        if text is None:
            text = it["text"]
        fire_off = off.decide(_event(it, text)).fire
        fire_on = on.decide(_event(it, text)).fire
        fire_on_raw = on.decide(_event(it, it["text"])).fire
        top5 = None
        if port is not None and fire_off:
            docs = await port.retrieve(text, top_k=5)
            top5 = [d.doc_id for d in docs]
        proc_in_top5 = bool(top5 and set(top5) & set(it["procedure_doc_ids"]))
        rows.append({
            "id": it["id"], "label": it["label"], "text": text, "text_source": text_src,
            "masked": "*" in text,
            "fired_without_rule": fire_off, "fired_with_rule": fire_on,
            "fired_with_rule_on_script_text": fire_on_raw,
            "top5_without_rule": top5, "procedure_in_top5": proc_in_top5,
        })

    suppressed = [r for r in rows if r["fired_without_rule"] and not r["fired_with_rule"]]
    risk = [r for r in rows if r["label"] == "needed" or r["procedure_in_top5"]]
    lost = [r for r in risk if r["fired_without_rule"] and not r["fired_with_rule"]]
    bc = [r for r in rows if r["label"] == "backchannel"]
    bc_sup = [r for r in bc if not r["fired_with_rule"]]
    b_rate = len(bc_sup) / len(bc) if bc else None
    a_ok = not lost
    b_ok = b_rate is not None and b_rate >= B_MIN
    return {
        "measured_on": date.today().isoformat(),
        "commit": _git_commit(),
        "command": " ".join(sys.argv),
        "host": f"{platform.system()} {platform.machine()}",
        "index": None if args.no_retrieval else args.index,
        "n": len(rows),
        "text_source_counts": {s: sum(r["text_source"] == s for r in rows) for s in ("e2e", "script")},
        "label_counts": labels["counts"],
        "A": {"risk_set": len(risk), "risk_needed": sum(r["label"] == "needed" for r in risk),
              "risk_procedure_in_top5_not_needed": sum(r["label"] != "needed" and r["procedure_in_top5"] for r in risk),
              "lost": [r["id"] for r in lost], "pass": a_ok},
        "B": {"backchannel": len(bc), "suppressed": len(bc_sup), "rate": b_rate, "min": B_MIN, "pass": b_ok,
              "not_suppressed": [{"id": r["id"], "text": r["text"]} for r in bc if r["fired_with_rule"]]},
        "report_only": {
            "other_suppressed": [{"id": r["id"], "text": r["text"]} for r in suppressed if r["label"] == "other"],
            "masked_turns": [{"id": r["id"], "label": r["label"], "text": r["text"], "fired_with_rule": r["fired_with_rule"]}
                             for r in rows if r["masked"]],
            "script_text_differs": [r["id"] for r in rows if r["fired_with_rule"] != r["fired_with_rule_on_script_text"]],
            "suppressed_total": len(suppressed),
        },
        "adopted": a_ok and b_ok,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="맞장구 억제 규칙 1회 측정 (decisions/216)")
    ap.add_argument("--index", default="callguard-kb-single")
    ap.add_argument("--device", default=None)
    ap.add_argument("--e2e-texts", type=Path, default=None)
    ap.add_argument("--no-retrieval", action="store_true", help="top-5 를 재지 않는다(위험 집합 = needed 만)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    res = asyncio.run(_run(args))
    summary = {k: v for k, v in res.items() if k != "rows"}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if args.out:
        args.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
