# Requirement: C-5, E-3
"""NER 교체 후보 비교 — 운영 koelectra-naver-ner(학습 데이터 동의서가 상업 이용 금지) vs vmaca123/korean-pii-ner-v3(CC-BY-SA-4.0).
같은 규칙 겹(LayeredMaskingAdapter) 위에서 ① 골든셋 STT 오류 곡선(같은 주입기·시드 3·최대 누락) ② 실제 AI Hub 고객 발화에서 NER 이 더 가린 구간.
후보의 라벨(NAME·ADDRESS)을 도메인이 쓰는 PER·LOC 로만 옮긴다 — 운영 코드는 고치지 않는다(오프라인 측정).
"""
import collections, glob, json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai"), str(ROOT / "scripts")]
from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter  # noqa: E402
from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger  # noqa: E402
from pii_ner.adapter.outbound.layered_masking_adapter import LayeredMaskingAdapter  # noqa: E402
from evaluation.golden_set import load_golden_set  # noqa: E402
import measure_error_tolerance as met  # noqa: E402

class MappedTagger(KoElectraNerTagger):
    MAP = {"NAME": "PER", "ADDRESS": "LOC"}
    def tag(self, text):
        out = []
        for t in super().tag(text):
            lab = self.MAP.get(t.label)
            if lab:
                out.append(type(t)(start=t.start, end=t.end, label=lab, score=t.score))
        return out

pieces_out = Path(sys.argv[1])
rule = RuleMaskingAdapter()
from huggingface_hub import snapshot_download
cand_dir = snapshot_download("vmaca123/korean-pii-ner-v3")
maskers = {"rule": rule,
           "rule+naver-ner(운영)": LayeredMaskingAdapter(RuleMaskingAdapter(), KoElectraNerTagger(ROOT / "models/koelectra-ner")),
           "rule+pii-ner-v3(후보)": LayeredMaskingAdapter(RuleMaskingAdapter(), MappedTagger(cand_dir))}
items = load_golden_set()
curve = met.masking_curve(items, maskers, met.SEEDS)
summary = {name: {f"{r['target']:.2f}": r["max_miss_count"] for r in rows} for name, rows in curve.items()}
print(json.dumps(summary, ensure_ascii=False))

rows = []
for f in sorted(glob.glob(str(ROOT / "data/raw/aihub-minwon-qa/validation/label/다산콜센터/*.json"))):
    rows += json.load(open(f, encoding="utf-8"))
texts = [t for t in ((r.get("고객질문(요청)") or r.get("고객답변") or "").strip() for r in rows if r.get("화자") != "상담사") if t]
real = {}; dump = []
for name in ("rule+naver-ner(운영)", "rule+pii-ner-v3(후보)"):
    added = []; types = collections.Counter()
    for t in texts:
        _, rs = rule.mask(t); _, ls = maskers[name].mask(t)
        rr = {s.span for s in rs}
        for s in ls:
            if s.span not in rr:
                added.append((s.type, t[s.span[0]:s.span[1]], t)); types[s.type] += 1
    real[name] = {"ner_added_spans": len(added), "by_type": dict(types)}
    for p, x, t in added: dump.append(f"{name}\t{p}\t「{x}」\t{t}")
pieces_out.write_text("\n".join(dump), encoding="utf-8")
res = {"curve_max_miss": summary, "real_customers": {"n": len(texts), **real}}
(ROOT / "eval/review-2026-10/results/ner_candidate_compare.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps(res, ensure_ascii=False))
