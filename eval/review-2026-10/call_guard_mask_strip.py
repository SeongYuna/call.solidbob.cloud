# Requirement: C-6, C-5, E-1
"""분류 전에 가림 표시(AI Hub 「OOO」·우리 마스킹 「*」)를 지우면 실제 고객 발화 오탐이 얼마나 주는지 — 입력 정리만(재학습 아님).
같은 정리를 외부 평가(APEACH·UnSmile)에도 똑같이 적용해 재현율이 안 깎이는지 함께 본다."""
import csv, glob, json, re, sys
from pathlib import Path
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
ROOT = Path(__file__).resolve().parents[2]
M = ROOT / sys.argv[1]
tok = AutoTokenizer.from_pretrained(M); model = AutoModelForSequenceClassification.from_pretrained(M).eval()
sys.path[:0] = [str(ROOT / "ai" / "apps")]
from call_guard.domain.services.mask_tokens import strip_mask_tokens as strip  # noqa: E402 — 운영 어댑터와 같은 함수
@torch.no_grad()
def pred(texts):
    out = []
    for i in range(0, len(texts), 64):
        b = [t if t else "." for t in texts[i:i+64]]
        out += model(**tok(b, padding=True, truncation=True, max_length=128, return_tensors="pt")).logits.argmax(-1).tolist()
    return out
def prf(y, p):
    tp = sum(a and b for a, b in zip(y, p)); fp = sum((not a) and b for a, b in zip(y, p)); fn = sum(a and not b for a, b in zip(y, p))
    return {"precision": round(tp/(tp+fp), 3) if tp+fp else 0, "recall": round(tp/(tp+fn), 3) if tp+fn else 0}
rows = []
for f in sorted(glob.glob(str(ROOT / "data/raw/aihub-minwon-qa/validation/label/다산콜센터/*.json"))):
    rows += json.load(open(f, encoding="utf-8"))
texts = [t for t in ((r.get("고객질문(요청)") or r.get("고객답변") or "").strip() for r in rows if r.get("화자") != "상담사") if t]
p_raw, p_strip = pred(texts), pred([strip(t) for t in texts])
ap = list(csv.DictReader(open(ROOT / "data/raw/apeach/test.csv", encoding="utf-8")))
un = [r for r in csv.DictReader(open(ROOT / "data/raw/unsmile/unsmile_valid_v1.0.tsv", encoding="utf-8"), delimiter="\t") if r["악플/욕설"] == "1" or r["clean"] == "1"]
res = {"model": sys.argv[1], "aihub_customers_flagged_raw": sum(p_raw), "aihub_customers_flagged_stripped": sum(p_strip), "n": len(texts),
       "APEACH_stripped": prf([int(r["class"]) for r in ap], pred([strip(r["text"]) for r in ap])),
       "UnSmile_stripped": prf([1 if r["악플/욕설"] == "1" else 0 for r in un], pred([strip(r["문장"]) for r in un])),
       "remaining_flagged": [t[:80] for t, a in zip(texts, p_strip) if a]}
print(json.dumps({k: v for k, v in res.items() if k != "remaining_flagged"}, ensure_ascii=False))
for t in res["remaining_flagged"]: print("  ", t)
res["remaining_flagged"] = len(res["remaining_flagged"])   # 원문 조각은 저장하지 않는다
(ROOT / f"eval/review-2026-10/results/call_guard_mask_strip_{M.name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
