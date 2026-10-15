# Requirement: B-2, E-1
"""조항 검색 임베딩 미세조정 — 생성 질문(doc2query, data/processed/train/retrieval-queries.jsonl) ↔ 조항(제목+본문) 짝으로 대조 학습.

손실: in-batch negatives 교차엔트로피(= sentence-transformers MultipleNegativesRankingLoss, scale 20) — 같은 배치의 다른 조항이 오답.
**골든셋은 학습에 쓰지 않는다**(평가 전용 — 생성 단계에서 같은 문장도 걸렀다).
KoE5(multilingual-e5 계열)는 `query: ` / `passage: ` 접두어 + mean pooling + L2 정규화 — 운영 임베딩과 같은 계산이다.

2026-10-15: sentence-transformers `fit` 은 `datasets` 를 요구해 운영 의존성과 충돌했고, **전체 학습(5.6억 파라미터 — 가중치+그래디언트+Adam
≈ 9GB)이 24GB 맥북을 두 번 멈췄다.** 그래서 torch·transformers 만으로 루프를 쓰고 `--train-top-layers` 로 위 N 개 층만 학습한다.
저장 형식은 원본 KoE5 폴더와 같다(가중치·토크나이저 + 풀링 설정 파일 복사) — `compare_embedders.py` · 운영 로더가 그대로 읽는다.

  .venv/bin/python scripts/train/finetune_retrieval_embedder.py --base models/koe5 --out models/koe5-ft --train-top-layers 6
"""
import argparse, json, random, shutil, sys, time
from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]
from retrieval.adapter.outbound.knowledge_base_loader import load_chunks  # noqa: E402
from retrieval.adapter.outbound.es_index import embedding_input  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True); ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--epochs", type=int, default=2); ap.add_argument("--batch", type=int, default=8)
ap.add_argument("--lr", type=float, default=2e-5); ap.add_argument("--seed", type=int, default=20261015)
ap.add_argument("--train-top-layers", type=int, default=6, help="0 = 전체 학습. N = 인코더 위 N 개 층만 학습")
ap.add_argument("--max-len", type=int, default=128); ap.add_argument("--scale", type=float, default=20.0)
a = ap.parse_args()
random.seed(a.seed); torch.manual_seed(a.seed)

base = ROOT / a.base
chunks = {c.chunk_id: c for c in load_chunks(ROOT / "knowledge-base")}
rows = [json.loads(l) for l in open(ROOT / "data/processed/train/retrieval-queries.jsonl", encoding="utf-8")]
pairs = [("query: " + r["query"], "passage: " + embedding_input(chunks[r["chunk_id"]]), r["chunk_id"]) for r in rows if r["chunk_id"] in chunks]

dev = "mps" if torch.backends.mps.is_available() else "cpu"
tok = AutoTokenizer.from_pretrained(str(base))
# MPS 의 sdpa 는 학습 중 드롭아웃을 지원하지 않는다 — eager 어텐션으로 올린다(계산 결과는 같다)
model = AutoModel.from_pretrained(str(base), attn_implementation="eager").to(dev)
if a.train_top_layers:
    for p in model.parameters():
        p.requires_grad = False
    for layer in model.encoder.layer[-a.train_top_layers:]:
        for p in layer.parameters():
            p.requires_grad = True
params = [p for p in model.parameters() if p.requires_grad]
trainable = sum(p.numel() for p in params)
print(f"학습 파라미터 {trainable/1e6:.1f}M / 전체 {sum(p.numel() for p in model.parameters())/1e6:.1f}M · 짝 {len(pairs)} · 장치 {dev}", flush=True)
opt = torch.optim.AdamW(params, lr=a.lr)


def encode(texts):
    enc = tok(texts, padding=True, truncation=True, max_length=a.max_len, return_tensors="pt").to(dev)
    h = model(**enc).last_hidden_state
    m = enc["attention_mask"].unsqueeze(-1).to(h.dtype)
    return F.normalize((h * m).sum(1) / m.sum(1).clamp(min=1e-9), p=2, dim=1)


def batches():
    # 같은 배치에 같은 조항이 두 번 들어가면 정답이 오답 칸에도 생긴다 — 조항이 겹치지 않게 묶는다
    order = pairs[:]; random.shuffle(order)
    out, cur, seen = [], [], set()
    for p in order:
        if p[2] in seen:
            continue
        cur.append(p); seen.add(p[2])
        if len(cur) == a.batch:
            out.append(cur); cur, seen = [], set()
    return out


model.train()
t0 = time.time(); log = []
for ep in range(a.epochs):
    bs = batches(); losses = []
    for i, b in enumerate(bs):
        q = encode([x[0] for x in b]); d = encode([x[1] for x in b])
        loss = F.cross_entropy(q @ d.T * a.scale, torch.arange(len(b), device=dev))
        opt.zero_grad(); loss.backward(); opt.step(); losses.append(loss.item())
        if i % 20 == 0:
            print(f"epoch {ep} step {i}/{len(bs)} loss {loss.item():.4f} · {time.time()-t0:.0f}s", flush=True)
    log.append({"epoch": ep, "batches": len(bs), "mean_loss": round(sum(losses) / len(losses), 4)})
    print(log[-1], flush=True)

model.eval()
a.out.mkdir(parents=True, exist_ok=True)
model.cpu().save_pretrained(str(a.out)); tok.save_pretrained(str(a.out))
for extra in ("modules.json", "config_sentence_transformers.json", "1_Pooling", "2_Normalize"):
    src = base / extra
    if src.is_dir():
        shutil.copytree(src, a.out / extra, dirs_exist_ok=True)
    elif src.exists():
        shutil.copy(src, a.out / extra)
meta = {"base": a.base, "train_pairs": len(pairs), "epochs": a.epochs, "batch": a.batch, "lr": a.lr, "seed": a.seed, "device": dev,
        "train_top_layers": a.train_top_layers or "all", "trainable_params_m": round(trainable / 1e6, 1), "max_len": a.max_len,
        "scale": a.scale, "loss_log": log, "seconds": round(time.time() - t0),
        "data": "doc2query by kanana-1.5-2.1b (골든셋과 같은 문장 제외 — 0건 겹침)"}
(a.out / "callguard_train_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
print(json.dumps(meta, ensure_ascii=False))
