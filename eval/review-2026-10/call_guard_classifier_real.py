# Requirement: C-6, E-1
"""학습한 폭언 분류기(models/call-guard-kcelectra)를 우리 환경에서 잰다 — ① 골든셋 C-6 15건(채점 전용, 학습 미사용) ② AI Hub 다산 실제 고객 발화 10,223건에서
폭언으로 붙인 비율(실제 상담은 폭언이 드물다 — 붙인 것 대부분이 오탐 후보, 표본을 읽어 판정) ③ CPU 지연(운영 장치). 원문 조각은 저장소 밖에.
"""
import csv, glob, json, random, sys, time
from pathlib import Path
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]
from call_guard.domain.services.detector import detect  # noqa: E402
from evaluation.golden_set import load_golden_set  # noqa: E402
M = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "models/call-guard-kcelectra")
tok = AutoTokenizer.from_pretrained(M); model = AutoModelForSequenceClassification.from_pretrained(M).eval()
@torch.no_grad()
def pred(texts, bs=64):
    out = []
    for i in range(0, len(texts), bs):
        enc = tok(texts[i:i+bs], padding=True, truncation=True, max_length=128, return_tensors="pt")
        out += model(**enc).logits.argmax(-1).tolist()
    return out
res = {}
g = [it for it in load_golden_set() if it.module == "C-6"]
raw = json.load(open(ROOT / "golden-set/v1-150.json"))["items"]
lab = {x["id"]: x.get("call_guard") for x in raw}
ys = [1 if (lab[it.id] or {}).get("type") in ("insult", "threat", "sexual") else 0 for it in g]
ps = pred([it.customer_utterance for it in g])
res["golden_c6"] = {"n": len(g), "abusive_labels": sum(ys), "classifier_hits_on_abusive": sum(1 for y, p in zip(ys, ps) if y and p),
                    "classifier_flags_on_non_abusive": sum(1 for y, p in zip(ys, ps) if not y and p),
                    "types": [ (lab[it.id] or {}).get("type") for it in g]}
rows = []
for f in sorted(glob.glob(str(ROOT / "data/raw/aihub-minwon-qa/validation/label/다산콜센터/*.json"))):
    rows += json.load(open(f, encoding="utf-8"))
texts = [t for t in ((r.get("고객질문(요청)") or r.get("고객답변") or "").strip() for r in rows if r.get("화자") != "상담사") if t]
t0 = time.time(); p = pred(texts); cpu_ms = (time.time() - t0) / len(texts) * 1000
flag = [t for t, x in zip(texts, p) if x]
lex = sum(1 for t in texts if any(d.category != "distress" for d in detect(t)))
random.seed(20261015)
Path(sys.argv[1]).write_text("\n".join(random.sample(flag, min(40, len(flag)))), encoding="utf-8")
res["aihub_customers"] = {"n": len(texts), "classifier_flagged": len(flag), "rate": round(len(flag) / len(texts), 4), "lexicon_flagged": lex,
                          "cpu_ms_per_utterance_batch64": round(cpu_ms, 2)}
t0 = time.time()
for t in texts[:200]: pred([t])
res["cpu_ms_single_utterance"] = round((time.time() - t0) / 200 * 1000, 1)
print(json.dumps(res, ensure_ascii=False))
(ROOT / f"eval/review-2026-10/results/call_guard_classifier_real_{Path(M).name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
