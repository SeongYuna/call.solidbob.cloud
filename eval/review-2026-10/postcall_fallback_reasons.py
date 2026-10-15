# Requirement: D-1, E-1
"""모델 요약이 규칙 초안으로 내려간 이유(검사 사유)를 통화별로 센다 — 같은 구성·같은 입력(temperature 0 · seed)."""
import asyncio, collections, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps"), str(ROOT / "ai")]
from evaluation.golden_set import load_postcall_set  # noqa: E402
from generation.adapter.outbound.ollama_chat import OllamaChat  # noqa: E402
from hub.app.dtos.transcript_dto import TranscriptEvent  # noqa: E402
from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter  # noqa: E402
from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger  # noqa: E402
from pii_ner.adapter.outbound.layered_masking_adapter import LayeredMaskingAdapter  # noqa: E402
from postcall.adapter.outbound.rule_postcall_adapter import RulePostcallAdapter  # noqa: E402
from postcall_summary.adapter.outbound.model_postcall_adapter import ModelPostcallAdapter  # noqa: E402
masker = LayeredMaskingAdapter(RuleMaskingAdapter(), KoElectraNerTagger(ROOT / "models/koelectra-ner"))
out = {}
for model in sys.argv[1:]:
    ad = ModelPostcallAdapter(RulePostcallAdapter(), chat=OllamaChat("http://localhost:11434", model=model, num_predict=160, timeout_s=30), retrieval=None)
    rows = []
    for c in load_postcall_set():
        segs = [TranscriptEvent(call_id=c.id, segment_id=i, speaker=s, text=masker.mask(t)[0], is_final=True) for i, s, t in c.turns]
        asyncio.run(ad.summarize(c.id, segs)); d = ad.last_detail
        rows.append({"call": c.id, "source": d.summary_source, "problems": list(d.problems), "raw_chars": len(d.raw_summary or "")})
    kinds = collections.Counter(p.split(" ")[0] + (" " + p.split(" ")[1] if len(p.split(" ")) > 1 else "") for r in rows for p in r["problems"])
    out[model] = {"model_used": sum(r["source"] == "model" for r in rows), "n": len(rows), "problem_kinds": dict(kinds), "calls": rows}
    print(model, out[model]["model_used"], "/", len(rows), dict(kinds))
(ROOT / "eval/review-2026-10/results/postcall_fallback_reasons.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
