# Requirement: D-1, E-1
"""심사 질문 22·23 — 통화 후 요약을 **모델(kanana 2.1B)로** 같은 골든셋(postcall-v1, 10통화·60항목)에 채점한다.
지금까지의 0.883 은 규칙 어댑터 값이었다. 운영과 같은 구성: 규칙+NER 마스킹 → ModelPostcallAdapter(폴백=규칙 초안).
채점은 하네스와 같은 함수(metrics.postcall.score_postcall — 허용 표기 글자 포함, 규칙). LLM 채점 없음.
추가 지표(규칙): 모델 요약이 실제로 나간 비율 · 원문(마스킹본)에 없는 숫자 수(summary_problems) · 통화당 소요 시간.
3회 실행, 최저 포함률을 보고한다(절대 원칙 4).
"""
import asyncio, json, sys, time
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
from postcall_summary.adapter.outbound.model_postcall_adapter import MODEL_SUMMARY_MARK, ModelPostcallAdapter  # noqa: E402
from postcall_summary.domain.services.rules import summary_problems  # noqa: E402

masker = LayeredMaskingAdapter(RuleMaskingAdapter(), KoElectraNerTagger(ROOT / "models/koelectra-ner"))
MODEL = sys.argv[2] if len(sys.argv) > 2 else "kanana-1.5-2.1b-instruct:q4_k_m"  # 운영과 같은 OllamaChat(temperature 0 · seed · think:false · num_predict 160 · 30초)
chat = OllamaChat("http://localhost:11434", model=MODEL, num_predict=160, timeout_s=30)
cases = load_postcall_set()
adapters = {"rule": RulePostcallAdapter(), "model": ModelPostcallAdapter(RulePostcallAdapter(), chat=chat, retrieval=None)}
runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
out = {}
for name, ad in adapters.items():
    per_run = []
    for r in range(runs if name == "model" else 1):
        scored, used_model, bad_digits, secs, samples = [], 0, 0, [], []
        for c in cases:
            segs = [TranscriptEvent(call_id=c.id, segment_id=i, speaker=s, text=masker.mask(t)[0], is_final=True)
                    for i, s, t in c.turns]
            t0 = time.time(); d = asyncio.run(ad.summarize(c.id, segs)); secs.append(time.time() - t0)
            transcript = "\n".join(s.text for s in segs)
            is_model = d.summary_text.endswith(MODEL_SUMMARY_MARK.strip()) or MODEL_SUMMARY_MARK.strip() in d.summary_text
            used_model += is_model
            probs = summary_problems(d.summary_text.replace(MODEL_SUMMARY_MARK, ""), transcript) if is_model else []
            bad_digits += sum(1 for p in probs if "숫자" in p)
            samples.append({"call": c.id, "model": is_model, "chars": len(d.summary_text), "problems": probs})
            scored.append(pm.PostcallCase(call_id=c.id, key_items=c.key_items, expected_type=c.inquiry_type,
                                          summary=d.summary_text, predicted_type=d.inquiry_type))
        s = pm.score_postcall(scored)
        per_run.append({"coverage_micro": s["coverage_micro"], "key_items_hit": s["key_items_hit"], "key_items": s["key_items"],
                        "coverage_by_kind": s.get("coverage_by_kind"), "model_summaries": used_model, "n_calls": len(cases),
                        "summaries_with_digit_problem": bad_digits, "sec_per_call_median": round(sorted(secs)[len(secs)//2], 2),
                        "chars_median": sorted(x["chars"] for x in samples)[len(samples)//2], "calls": samples})
        print(name, r + 1, json.dumps({k: v for k, v in per_run[-1].items() if k != "calls"}, ensure_ascii=False), flush=True)
    out[name] = {"runs": per_run, "min_coverage": min(p["coverage_micro"] for p in per_run)}
tag = "" if MODEL.startswith("kanana") else "_" + MODEL.split("/")[-1].split(":")[0].lower()
out["model_name"] = MODEL
dst = ROOT / f"eval/review-2026-10/results/postcall_model_eval{tag}.json"
dst.write_text(json.dumps(out, ensure_ascii=False, indent=1))
