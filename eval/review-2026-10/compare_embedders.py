# Requirement: B-2, E-1
"""심사 질문 12 — 임베딩 모델 비교. 같은 98조항(ES 색인 원문, 제목+본문 = 운영 embedding_input 과 같은 입력),
같은 질의(harness.retrieval_query), 같은 채점(metrics.retrieval) 으로 **메모리 안에서** 코사인 상위 5를 비교한다.
골든셋·색인·운영 코드는 고치지 않는다. 장치는 CPU 고정.
"""
from __future__ import annotations
import json, sys, time, urllib.request
from pathlib import Path
import torch
from transformers import AutoModel, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai")]
from evaluation.golden_set import load_golden_set  # noqa: E402
from evaluation.harness import retrieval_query  # noqa: E402
from evaluation.metrics.retrieval import aggregate_recall_mrr  # noqa: E402

MODELS = {  # 이름: (경로·HF id, 질의 접두어, 문서 접두어, pooling, max_len)
    "KoE5 (운영)": (str(ROOT / "models/koe5"), "query: ", "passage: ", "mean", 512),
    "ko-sroberta-multitask (이전 후보)": (str(ROOT / "models/ko-sroberta-multitask"), "", "", "mean", 128),
    "multilingual-e5-base": ("intfloat/multilingual-e5-base", "query: ", "passage: ", "mean", 512),
    "bge-m3": ("BAAI/bge-m3", "", "", "cls", 512),
    # 2026-10-15 미세조정본(decisions/223) — doc2query 생성 질문으로 학습, 골든셋 미사용
    "KoE5-ft (도메인 미세조정)": (str(ROOT / "models/koe5-ft"), "query: ", "passage: ", "mean", 512),
}

def embed(tok, model, texts, pooling, max_len):
    out = []
    for i in range(0, len(texts), 16):
        enc = tok(texts[i:i+16], padding=True, truncation=True, max_length=max_len, return_tensors="pt")
        with torch.no_grad():
            h = model(**enc).last_hidden_state
        if pooling == "cls":
            v = h[:, 0]
        else:
            m = enc["attention_mask"].unsqueeze(-1).to(h.dtype)
            v = (h * m).sum(1) / m.sum(1).clamp(min=1e-9)
        out.append(torch.nn.functional.normalize(v, p=2, dim=1))
    return torch.cat(out)

def main():
    # 지식베이스 파일에서 직접 청크를 만든다 — 색인과 같은 로더·같은 입력(제목+본문). 로컬 ES 색인은 4.23 추가 전 판이라 쓰지 않는다
    from retrieval.adapter.outbound.knowledge_base_loader import load_chunks
    from retrieval.adapter.outbound.es_index import embedding_input
    chunks = load_chunks(ROOT / "knowledge-base")
    ids = [c.doc_id for c in chunks]
    passages = [embedding_input(c) for c in chunks]
    print(f"청크 {len(chunks)} · 조항 {len(set(ids))}")
    items = [it for it in load_golden_set() if it.module == "B" and it.expected_doc_ids]
    queries = [retrieval_query(it) for it in items]
    only = sys.argv[1:] or list(MODELS)
    results = {}
    for name in only:
        path, qp, pp, pooling, max_len = MODELS[name]
        t0 = time.time()
        tok = AutoTokenizer.from_pretrained(path); model = AutoModel.from_pretrained(path).eval()
        P = embed(tok, model, [pp + p for p in passages], pooling, max_len)
        tq = time.time()
        Q = embed(tok, model, [qp + q for q in queries], pooling, max_len)
        per_q_ms = (time.time() - tq) / len(queries) * 1000
        top = (Q @ P.T).topk(5, dim=1).indices.tolist()
        got = [[ids[j] for j in row] for row in top]
        agg = aggregate_recall_mrr(list(zip([it.expected_doc_ids for it in items], got)), k=5)
        missed = [it.id for it, g in zip(items, got) if not set(it.expected_doc_ids) & set(g)]
        size_mb = sum(p.numel() for p in model.parameters()) * 4 / 1e6
        results[name] = {**agg, "n": len(items), "missed": missed, "query_embed_ms_cpu": round(per_q_ms, 1),
                         "params_fp32_mb": round(size_mb), "pooling": pooling, "max_len": max_len, "total_s": round(time.time() - t0, 1)}
        print(name, json.dumps(results[name], ensure_ascii=False))
        del model
    out = ROOT / "eval/review-2026-10/results/compare_embedders.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    prev = json.loads(out.read_text()) if out.exists() else {}
    prev.update(results); out.write_text(json.dumps(prev, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
