#!/usr/bin/env python3
# Requirement: B-6, B-2, E-1
"""B-6 「관련 문서 없음」 문턱 측정 — 정답 있음(B 96건)과 정답 없음(B-6) 의 **1순위 점수 분포**를 검색 구성별로 나란히 잰다.

    export ELASTICSEARCH_URL=http://localhost:9200
    .venv/bin/python scripts/measure_no_answer_threshold.py --device mps            # bm25 · dense · rerank-dense
    .venv/bin/python scripts/measure_no_answer_threshold.py --only bm25 --out x.json

**판정 로직이 아니라 측정이다.** 문턱을 코드에 넣지 않는다 — 여기서 나온 표를 보고 팀이 정한다
(`w5-b6-no-answer-threshold`, 절대 원칙 9 는 「판정은 규칙이 한다」이지 「규칙 값을 이 스크립트가 고른다」가 아니다).

점수 눈금은 구성마다 다르다 — BM25 는 ES raw `_score`(상한 없음) · dense 는 ES cosine 유사도(`(1+cos)/2`, 0~1) ·
rerank-dense 는 bge-reranker **로짓**(음수 가능). 구성 사이의 값을 비교하지 않는다.

「정답 있음」의 기준 분포는 두 벌 낸다 — ① B 96건 전체의 1순위 점수 ② 그중 **상위 5에 정답이 든** 항목만. 문턱이
「정답을 잃는」 것은 ②에서 세는 것이 맞다(①의 나머지는 문턱 없이도 이미 틀린 항목이다). 표는 둘 다 찍는다.

검색·질의 산식은 하네스와 같다(`evaluation.harness.retrieval_query` · `scripts/run_eval.build_retriever`). 새로 쓰지 않는다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "scripts")]

from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from evaluation.metrics.retrieval import hit_at_k  # noqa: E402
from run_eval import _es_client, _git_commit, build_retriever  # noqa: E402

KINDS = ("bm25", "dense", "rerank-dense")
REFERRAL_DOC = "DASAN-MANUAL-2.2"  # 「소관이 아닌 문의의 처리」 — 이게 뜨면 「없음」이 아니라 「소관 안내」가 답일 수 있다


def _summary(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    s = sorted(xs)
    q = lambda p: s[min(len(s) - 1, int(round(p * (len(s) - 1))))]  # noqa: E731
    return {"n": len(s), "min": s[0], "p10": q(0.10), "p25": q(0.25), "median": statistics.median(s),
            "p75": q(0.75), "p90": q(0.90), "max": s[-1]}


def _sweep(have: list[float], none: list[float]) -> list[dict]:
    """문턱 t(1순위 점수 < t 면 기권) 후보마다 「정답 있음 잃음 / 정답 없음 걸러냄」. 후보는 두 분포의 값 전체."""
    cands = sorted(set(have) | set(none))
    rows = []
    for t in cands:
        rows.append({"t": t, "have_lost": sum(1 for x in have if x < t), "none_filtered": sum(1 for x in none if x < t)})
    return rows


def _pick_rows(sweep: list[dict], n_have: int, n_none: int) -> list[dict]:
    """표에 실을 대표 문턱 — 정답 0건 잃는 최대 문턱 · 정답 없음 전부 거르는 최소 문턱 · 손실 1·2·3·5건 지점."""
    out = {}
    zero_loss = [r for r in sweep if r["have_lost"] == 0]
    if zero_loss:
        r = max(zero_loss, key=lambda r: r["t"]); out["정답 0건 잃는 최대 문턱"] = r
    all_f = [r for r in sweep if r["none_filtered"] == n_none]
    if all_f:
        r = min(all_f, key=lambda r: r["t"]); out["정답 없음 전부 거르는 최소 문턱"] = r
    for k in (1, 2, 3, 5, 10):
        rs = [r for r in sweep if r["have_lost"] <= k]
        if rs:
            r = max(rs, key=lambda r: (r["none_filtered"], -r["t"])); out[f"정답 ≤{k}건 잃을 때 최대 걸러냄"] = r
    return [{"label": k, **v} for k, v in out.items()]


async def _measure(port, items, *, top_k: int = 5) -> list[dict]:
    rows = []
    for it in items:
        docs = await port.retrieve(retrieval_query(it), top_k=top_k)
        ids = [d.doc_id for d in docs]
        rows.append({
            "id": it.id, "module": it.module,
            "top1_id": ids[0] if ids else None,
            "top1_score": docs[0].score if docs else None,
            "hit5": hit_at_k(it.expected_doc_ids, ids) if it.expected_doc_ids else None,
            "top1_correct": (ids[0] in it.expected_doc_ids) if (ids and it.expected_doc_ids) else None,
            "referral_rank": (ids.index(REFERRAL_DOC) + 1) if REFERRAL_DOC in ids else None,
            "abstained": not docs,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="B-6 정답 없음 문턱 측정 — 1순위 점수 분포")
    ap.add_argument("--golden-set", type=Path, default=ROOT / "golden-set" / "v1-150.json")
    ap.add_argument("--only", default=",".join(KINDS))
    ap.add_argument("--device", default=None)
    ap.add_argument("--out", type=Path, default=None, help="측정 원자료 JSON")
    ap.add_argument("--no-answer-set", type=Path, default=None,
                    help="정답 없음(B-6) 항목을 이 파일에서 읽는다 — 보류 표본(held-out) 재측정용(decisions/215). "
                         "정답 있음(B)은 그대로 --golden-set 에서")
    ap.add_argument("--at", type=float, action="append", default=[],
                    help="미리 정한 문턱 t 에서의 「정답 잃음 · 걸러냄」을 따로 찍는다(여러 번 줄 수 있다). 문턱을 고르지 않는다")
    args = ap.parse_args()

    client = _es_client(os.environ.get("ELASTICSEARCH_URL"))
    if client is None:
        raise SystemExit("ELASTICSEARCH_URL 이 없다 — 이 측정은 ES 없이 못 한다")
    items = load_golden_set(args.golden_set)
    b_items = [it for it in items if it.module == "B"]
    b6_source = load_golden_set(args.no_answer_set) if args.no_answer_set else items
    b6_items = [it for it in b6_source if it.module == "B-6"]
    # 유형(no_answer_category)은 GoldenItem 에 없는 필드라 원본 JSON 에서 읽는다 — 유형별 걸러냄을 찍으려고
    raw = json.loads((args.no_answer_set or args.golden_set).read_text(encoding="utf-8"))
    category = {e["id"]: e.get("no_answer_category") for e in raw["items"] if e.get("module") == "B-6"}
    if not b6_items:
        raise SystemExit("골든셋에 B-6 항목이 0건이다 — 잴 것이 없다")

    meta = {"date": date.today().isoformat(), "commit": _git_commit(), "golden_set": args.golden_set.name,
            "n_have": len(b_items), "n_none": len(b6_items),
            "no_answer_set": args.no_answer_set.name if args.no_answer_set else args.golden_set.name, "device": args.device or "cpu",
            "platform": f"{platform.system()} {platform.machine()}", "python": platform.python_version()}
    print(json.dumps(meta, ensure_ascii=False))
    result = {"meta": meta, "kinds": {}}
    from retrieval.adapter.outbound.es_index import SINGLE_INDEX

    for kind in [k.strip() for k in args.only.split(",") if k.strip()]:
        port = build_retriever(client, index=SINGLE_INDEX, kind=kind, device=args.device)
        rows = asyncio.run(_measure(port, b_items + b6_items))
        have = [r for r in rows if r["module"] == "B"]
        none = [r for r in rows if r["module"] == "B-6"]
        for r in none:
            r["category"] = category.get(r["id"])
        have_all = [r["top1_score"] for r in have if r["top1_score"] is not None]
        have_hit = [r["top1_score"] for r in have if r["top1_score"] is not None and r["hit5"]]
        none_s = [r["top1_score"] for r in none if r["top1_score"] is not None]
        sweep_all = _sweep(have_all, none_s)
        sweep_hit = _sweep(have_hit, none_s)
        overlap = (min(have_hit) if have_hit else None, max(none_s) if none_s else None)
        summary = {
            "have_all": _summary(have_all), "have_hit5": _summary(have_hit), "none": _summary(none_s),
            "have_hit5_count": sum(1 for r in have if r["hit5"]),
            "none_abstained": sum(1 for r in none if r["abstained"]),
            "none_referral_in_top5": sum(1 for r in none if r["referral_rank"]),
            "none_referral_top1": sum(1 for r in none if r["referral_rank"] == 1),
            "none_top1_ids": sorted({r["top1_id"] for r in none if r["top1_id"]}),
            "overlap": {"have_hit5_min": overlap[0], "none_max": overlap[1],
                        "separable": (overlap[0] is not None and overlap[1] is not None and overlap[1] < overlap[0])},
            "picks_vs_hit5": _pick_rows(sweep_hit, len(have_hit), len(none_s)),
            "picks_vs_all": _pick_rows(sweep_all, len(have_all), len(none_s)),
            "at": [_at(t, have, none) for t in args.at],
        }
        result["kinds"][kind] = {"summary": summary, "rows": rows, "sweep_hit5": sweep_hit}
        _print(kind, summary, none)

    if args.out:
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n원자료: {args.out}")
    return 0


def _at(t: float, have: list[dict], none: list[dict]) -> dict:
    """미리 정한 문턱 t 하나에서 — 1순위 점수 < t 면 기권. 「정답 잃음」은 상위5 적중 항목 기준(표의 정의와 같다)."""
    below = lambda r: r["top1_score"] is not None and r["top1_score"] < t  # noqa: E731
    cats: dict[str, list[int]] = {}
    for r in none:
        c = cats.setdefault(r.get("category") or "?", [0, 0])
        c[1] += 1
        c[0] += below(r)
    return {"t": t,
            "have_hit5_lost": sorted(r["id"] for r in have if r["hit5"] and below(r)),
            "have_hit5_n": sum(1 for r in have if r["hit5"]),
            "have_all_abstained": sorted(r["id"] for r in have if below(r)),
            "have_all_n": len(have),
            "none_filtered": sum(1 for r in none if below(r)), "none_n": len(none),
            "none_by_category": {k: f"{v[0]}/{v[1]}" for k, v in cats.items()},
            "none_kept": sorted(r["id"] for r in none if not below(r))}


def _fmt(x):
    return "—" if x is None else f"{x:.4f}"


def _print(kind: str, s: dict, none_rows: list[dict]) -> None:
    print(f"\n=== {kind} ===")
    for name, key in (("정답 있음 (B 전체)", "have_all"), ("정답 있음 (상위5 적중만)", "have_hit5"), ("정답 없음 (B-6)", "none")):
        d = s[key]
        print(f"  {name:<22} n={d['n']:<3} min={_fmt(d.get('min'))} p10={_fmt(d.get('p10'))} p25={_fmt(d.get('p25'))} "
              f"med={_fmt(d.get('median'))} p75={_fmt(d.get('p75'))} p90={_fmt(d.get('p90'))} max={_fmt(d.get('max'))}")
    o = s["overlap"]
    print(f"  적중 최소 {_fmt(o['have_hit5_min'])} vs 없음 최대 {_fmt(o['none_max'])} → "
          f"{'문턱 하나로 가른다' if o['separable'] else '겹친다 — 문턱 하나로 못 가른다'}")
    print(f"  B-6 기권 {s['none_abstained']} · MANUAL-2.2(소관 안내) 상위5 {s['none_referral_in_top5']} / 1순위 {s['none_referral_top1']}")
    print(f"  B-6 1순위에 뜬 조항: {', '.join(s['none_top1_ids'])}")
    print("  문턱 후보 (상위5 적중 항목 기준 손실):")
    for r in s["picks_vs_hit5"]:
        print(f"    {r['label']:<28} t={r['t']:.4f}  정답 잃음 {r['have_lost']:>2}  정답 없음 걸러냄 {r['none_filtered']:>2}")
    for a in s.get("at", []):
        print(f"  [t={a['t']}] 정답 잃음(상위5 적중 {a['have_hit5_n']}건 중) {len(a['have_hit5_lost'])} {a['have_hit5_lost']} · "
              f"B 전체 {a['have_all_n']}건 중 기권 {len(a['have_all_abstained'])} · "
              f"정답 없음 걸러냄 {a['none_filtered']}/{a['none_n']} {a['none_by_category']}")
    print("  B-6 항목별 1순위:")
    for r in none_rows:
        print(f"    {r['id']} {_fmt(r['top1_score'])} {r['top1_id']}")


if __name__ == "__main__":
    raise SystemExit(main())
