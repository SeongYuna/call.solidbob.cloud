# Requirement: C-6, E-1
"""C-6 폭언 분류기 학습 — KcELECTRA-base(로컬 models/kcelectra-base, MIT) 를 kocohub 「korean-hate-speech」(CC-BY-SA-4.0) 로 이진 미세조정.

라벨: hate·offensive → 1(폭언) · none → 0. 모델 선택은 kocohub **dev** 로만 한다(검증 F1 최고 epoch).
평가는 **학습·선택에 한 번도 쓰지 않은 외부 데이터** 둘: APEACH test(CC-BY-SA-4.0) · UnSmile valid(CC-BY-NC-ND — 측정만, 가중치·데이터 재배포 없음).
같은 데이터에서 지금 운영 어휘 사전(ai/apps/call_guard)을 나란히 잰다. 장치: MPS(맥북 M5) → 없으면 CPU.
골든셋(v1-150)의 C-6 15건은 학습에 쓰지 않는다(채점 전용).

  <trainenv>/bin/python scripts/train/train_call_guard_classifier.py --epochs 3 --out models/call-guard-kcelectra
"""
import argparse, csv, glob, json, random, sys, time
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]
from call_guard.domain.services.detector import detect  # noqa: E402

def read_koco(name):
    rows = list(csv.DictReader(open(ROOT / f"data/raw/korean-hate-speech/labeled/{name}.tsv", encoding="utf-8"), delimiter="\t"))
    return [r["comments"] for r in rows], [0 if r["hate"] == "none" else 1 for r in rows]
def read_indomain_negatives(n, seed):
    """통화 도메인 정상 발화 — AI Hub 「고객 응대 음성」·「상담 음성」 전사(validation). 약한 라벨: 폭언 아님(0).
    평가에 쓰는 AI Hub 「민원 질의응답」 과 **다른 데이터셋**이다. 전사 기호(n/ b/ l/ (철자)/(발음))는 지운다."""
    import re
    files = sorted(glob.glob(str(ROOT / "data/raw/aihub-ktelspeech/**/*.txt"), recursive=True)) + \
            sorted(glob.glob(str(ROOT / "data/raw/aihub-krespspeech/**/*.txt"), recursive=True))
    texts = []
    for f in files:
        t = open(f, encoding="utf-8", errors="ignore").read().strip()
        t = re.sub(r"\(([^)]*)\)/\(([^)]*)\)", r"\1", t); t = re.sub(r"\b[nblou]/\s*", "", t); t = re.sub(r"\s+", " ", t).strip()
        if 4 <= len(t) <= 200: texts.append(t)
    random.Random(seed).shuffle(texts)
    return texts[:n], texts[n:n + 1000]   # 학습용 · 선택용(검증)

def read_apeach():
    rows = list(csv.DictReader(open(ROOT / "data/raw/apeach/test.csv", encoding="utf-8")))
    return [r["text"] for r in rows], [int(r["class"]) for r in rows]
def read_unsmile():
    rows = list(csv.DictReader(open(ROOT / "data/raw/unsmile/unsmile_valid_v1.0.tsv", encoding="utf-8"), delimiter="\t"))
    rows = [r for r in rows if r["악플/욕설"] == "1" or r["clean"] == "1"]   # 욕설 vs 깨끗 — 혐오 대상만 있는 문장은 뺀다(라벨 체계가 다름)
    return [r["문장"] for r in rows], [1 if r["악플/욕설"] == "1" else 0 for r in rows]

def prf(y, p):
    tp = sum(1 for a, b in zip(y, p) if a == 1 and b == 1); fp = sum(1 for a, b in zip(y, p) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y, p) if a == 1 and b == 0)
    pr = tp / (tp + fp) if tp + fp else 0.0; rc = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(pr, 3), "recall": round(rc, 3), "f1": round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0,
            "n": len(y), "positives": sum(y)}

@torch.no_grad()
def predict(model, tok, texts, dev, bs=64):
    model.eval(); out = []
    for i in range(0, len(texts), bs):
        enc = tok(texts[i:i+bs], padding=True, truncation=True, max_length=128, return_tensors="pt").to(dev)
        out += model(**enc).logits.argmax(-1).cpu().tolist()
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--epochs", type=int, default=3); ap.add_argument("--seed", type=int, default=20261015)
    ap.add_argument("--out", type=Path, default=ROOT / "models/call-guard-kcelectra"); ap.add_argument("--neg-indomain", type=int, default=0)
    ap.add_argument("--result", default="call_guard_classifier.json"); args = ap.parse_args()
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(ROOT / "models/kcelectra-base")
    model = AutoModelForSequenceClassification.from_pretrained(ROOT / "models/kcelectra-base", num_labels=2).to(dev)
    xtr, ytr = read_koco("train"); xdv, ydv = read_koco("dev")
    neg_val = []
    if args.neg_indomain:
        neg_tr, neg_val = read_indomain_negatives(args.neg_indomain, args.seed)
        xtr += neg_tr; ytr += [0] * len(neg_tr)
        xdv += neg_val; ydv += [0] * len(neg_val)   # 선택(검증)에도 도메인 정상 발화 1,000 을 넣어 오탐을 같이 본다
    idx = list(range(len(xtr)))
    opt = torch.optim.AdamW(model.parameters(), lr=3e-5, weight_decay=0.01)
    steps = (len(idx) // 32 + 1) * args.epochs
    sch = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    best, log = -1, []
    t0 = time.time()
    for ep in range(1, args.epochs + 1):
        model.train(); random.shuffle(idx)
        for i in range(0, len(idx), 32):
            b = idx[i:i+32]
            enc = tok([xtr[j] for j in b], padding=True, truncation=True, max_length=128, return_tensors="pt").to(dev)
            loss = model(**enc, labels=torch.tensor([ytr[j] for j in b], device=dev)).loss
            loss.backward(); opt.step(); sch.step(); opt.zero_grad()
        m = prf(ydv, predict(model, tok, xdv, dev)); m["epoch"] = ep; m["elapsed_s"] = round(time.time() - t0); log.append(m)
        print("dev", m, flush=True)
        if m["f1"] > best:
            best = m["f1"]; args.out.mkdir(parents=True, exist_ok=True); model.save_pretrained(args.out); tok.save_pretrained(args.out)
    model = AutoModelForSequenceClassification.from_pretrained(args.out).to(dev)
    res = {"base": "models/kcelectra-base (beomi/KcELECTRA-base, MIT)", "train": "kocohub korean-hate-speech train 7,896 (CC-BY-SA-4.0)",
           "select": "kocohub dev 471" + (f" + 통화 도메인 정상 발화 {len(neg_val)}" if neg_val else ""), "indomain_negatives_train": args.neg_indomain, "device": dev, "seed": args.seed, "epochs": args.epochs, "dev_log": log, "external": {}}
    for name, (x, y) in {"APEACH test": read_apeach(), "UnSmile valid (욕설 vs clean)": read_unsmile()}.items():
        t1 = time.time(); p = predict(model, tok, x, dev); ms = (time.time() - t1) / len(x) * 1000
        lex = [1 if any(d.category != "distress" for d in detect(t)) else 0 for t in x]
        res["external"][name] = {"classifier": {**prf(y, p), "ms_per_text": round(ms, 2)}, "lexicon(운영)": prf(y, lex),
                                 "union(사전 ∪ 분류기)": prf(y, [max(a, b) for a, b in zip(p, lex)])}
        print(name, json.dumps(res["external"][name], ensure_ascii=False), flush=True)
    (ROOT / "eval/review-2026-10/results" / args.result).write_text(json.dumps(res, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
