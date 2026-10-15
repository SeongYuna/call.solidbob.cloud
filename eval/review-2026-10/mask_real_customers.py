# Requirement: C-5, E-1
"""심사 질문 7·8 — AI Hub 다산 실제 고객 발화 전체에 운영과 같은 두 겹(규칙 + koelectra NER)을 돌려 **탐지 건수**를 센다.
정답 라벨이 없으므로 재현율이라 부르지 않는다. 과잉(오탐)은 무작위 표본 조각을 사람이 읽고 판정하기 위해 따로 뽑는다.
원문 조각은 저장소에 남기지 않는다(출력 경로는 인자로 저장소 밖). 숫자 요약만 results/ 에 남긴다.
"""
import collections, glob, json, random, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]
from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter  # noqa: E402
from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger  # noqa: E402
from pii_ner.adapter.outbound.layered_masking_adapter import LayeredMaskingAdapter  # noqa: E402

pieces_out = Path(sys.argv[1])  # 저장소 밖
rows = []
for f in sorted(glob.glob(str(ROOT / "data/raw/aihub-minwon-qa/validation/label/다산콜센터/*.json"))):
    rows += json.load(open(f, encoding="utf-8"))
texts = [(r.get("고객질문(요청)") or r.get("고객답변") or "").strip() for r in rows if r.get("화자") != "상담사"]
texts = [t for t in texts if t]
rule = RuleMaskingAdapter()
layered = LayeredMaskingAdapter(rule, KoElectraNerTagger(ROOT / "models/koelectra-ner"))
by_rule, by_all, ner_only = collections.Counter(), collections.Counter(), []
utt_any = 0; t0 = time.time()
for t in texts:
    _, rs = rule.mask(t); _, ls = layered.mask(t)
    by_rule.update(s.type for s in rs); by_all.update(s.type for s in ls)
    utt_any += bool(ls)
    rr = {s.span for s in rs}
    ner_only += [(s.type, t[s.span[0]:s.span[1]], t) for s in ls if s.span not in rr]
random.seed(20261013)
sample = random.sample(ner_only, min(60, len(ner_only)))
pieces_out.write_text("\n".join(f"{i:02d}\t{p}\t「{x}」\t{t}" for i, (p, x, t) in enumerate(sample)), encoding="utf-8")
res = {"customer_utterances": len(texts), "utterances_with_any_mask": utt_any, "spans_rule_only_pipeline": dict(by_rule),
       "spans_rule_plus_ner": dict(by_all), "ner_added_spans": len(ner_only), "sample_for_manual_review": len(sample),
       "seconds_cpu": round(time.time() - t0, 1)}
out = ROOT / "eval/review-2026-10/results/mask_real_customers.json"
out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps(res, ensure_ascii=False))
