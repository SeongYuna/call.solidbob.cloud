# Requirement: B-2, A-5, E-1
"""다국어 조항 검색 비교 — 외국인 고객이 모국어(영어·베트남어·중국어)로 물을 때 한국어 지식베이스(99조항)에서 정답 조항을 찾는가.
질의: eval/review-2026-10/multilingual_queries.json(Claude 번역 · 사람 검토 전, 40문항). 정답 조항: 골든셋 v1-150.2 그대로.
비교 방식은 compare_embedders.py 와 같다(메모리 안 코사인 · 운영 KoE5 값을 그대로 재현한 방식).
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai"), str(Path(__file__).parent)]
from transformers import AutoModel, AutoTokenizer  # noqa: E402
from compare_embedders import MODELS, embed  # noqa: E402
from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from evaluation.metrics.retrieval import aggregate_recall_mrr  # noqa: E402
from retrieval.adapter.outbound.knowledge_base_loader import load_chunks  # noqa: E402
from retrieval.adapter.outbound.es_index import embedding_input  # noqa: E402

extra = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)   # 이름=경로(미세조정 모델 등)
names = [a for a in sys.argv[1:] if "=" not in a] or ["KoE5 (운영)", "bge-m3", "multilingual-e5-base", "ko-sroberta-multitask (이전 후보)"]
for k, v in extra.items():
    base = MODELS["bge-m3"] if "bge" in k.lower() else MODELS["KoE5 (운영)"]
    MODELS[k] = (v, *base[1:]); names.append(k)
ml = json.load(open(Path(__file__).parent / "multilingual_queries.json"))
gold = {it.id: it for it in load_golden_set()}
rows = [(gold[q["id"]], q) for q in ml["items"]]
chunks = load_chunks(ROOT / "knowledge-base"); ids = [c.doc_id for c in chunks]
res = {}
for name in names:
    path, qp, pp, pooling, ml_ = MODELS[name]
    tok = AutoTokenizer.from_pretrained(path); model = AutoModel.from_pretrained(path).eval()
    P = embed(tok, model, [pp + embedding_input(c) for c in chunks], pooling, ml_)
    res[name] = {}
    for lang in ("ko", "en", "vi", "zh"):
        qs = [retrieval_query(g) if lang == "ko" else q[lang] for g, q in rows]
        Q = embed(tok, model, [qp + x for x in qs], pooling, ml_)
        got = [[ids[j] for j in r] for r in (Q @ P.T).topk(5, dim=1).indices.tolist()]
        s = aggregate_recall_mrr(list(zip([g.expected_doc_ids for g, _ in rows], got)))
        res[name][lang] = {"recall_at_5": round(s["recall_at_k"], 3), "hits": round(s["recall_at_k"] * s["n"]), "mrr": round(s["mrr"], 3), "n": s["n"]}
    print(name, json.dumps(res[name], ensure_ascii=False), flush=True)
out = Path(__file__).parent / "results/multilingual_compare.json"
prev = json.loads(out.read_text()) if out.exists() else {}
prev.update(res); out.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
