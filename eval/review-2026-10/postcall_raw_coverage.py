# Requirement: D-1, E-1
"""모델 원출력(검사·폴백 전) 자체의 핵심 항목 포함률 — 운영 구성 값(검사 후 폴백 섞임)과 따로 본다. 같은 채점(score_postcall), 3회 최저."""
import asyncio, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai")]
from evaluation.golden_set import load_postcall_set  # noqa: E402
from evaluation.metrics import postcall as pm  # noqa: E402
from generation.adapter.outbound.ollama_chat import OllamaChat  # noqa: E402
from hub.app.dtos.transcript_dto import TranscriptEvent  # noqa: E402
from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter  # noqa: E402
from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger  # noqa: E402
from pii_ner.adapter.outbound.layered_masking_adapter import LayeredMaskingAdapter  # noqa: E402
from postcall.adapter.outbound.rule_postcall_adapter import RulePostcallAdapter  # noqa: E402
from postcall_summary.adapter.outbound.model_postcall_adapter import ModelPostcallAdapter  # noqa: E402
masker = LayeredMaskingAdapter(RuleMaskingAdapter(), KoElectraNerTagger(ROOT / "models/koelectra-ner"))
cases = load_postcall_set(); out = {}
for model in sys.argv[1:]:
    ad = ModelPostcallAdapter(RulePostcallAdapter(), chat=OllamaChat("http://localhost:11434", model=model, num_predict=160, timeout_s=30), retrieval=None)
    runs = []
    for _ in range(3):
        scored, numbered, chars = [], 0, []
        for c in cases:
            segs = [TranscriptEvent(call_id=c.id, segment_id=i, speaker=s, text=masker.mask(t)[0], is_final=True) for i, s, t in c.turns]
            asyncio.run(ad.summarize(c.id, segs)); raw = ad.last_detail.raw_summary or ""
            numbered += bool(re.search(r"(^|\n)\s*\d+[.)]\s", raw)); chars.append(len(raw))
            scored.append(pm.PostcallCase(call_id=c.id, key_items=c.key_items, expected_type=c.inquiry_type, summary=raw, predicted_type=None))
        s = pm.score_postcall(scored)
        runs.append({"coverage_micro": s["coverage_micro"], "hit": s["key_items_hit"], "by_kind": s.get("coverage_by_kind"),
                     "numbered_list_outputs": numbered, "chars_median": sorted(chars)[len(chars)//2]})
    out[model] = {"min_coverage": min(r["coverage_micro"] for r in runs), "runs": runs}
    print(model, json.dumps(runs[0], ensure_ascii=False), "min", out[model]["min_coverage"])
(ROOT / "eval/review-2026-10/results/postcall_raw_coverage.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
