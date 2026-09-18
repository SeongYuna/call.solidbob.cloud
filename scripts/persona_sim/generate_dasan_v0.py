# Requirement: B-1, C-1, C-2, C-3, C-5, C-6, D-5, J-5, J-6
"""합성 통화 대본 dasan-v0 생성·검증. 라벨 문구가 발화 안에 실제로 있는지 확인한 뒤에만 쓴다."""
import json, sys
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent / "dasan-v0"
GEN = "Claude Code (claude-opus-5) · 2026-09-16 · 사람 검토 전"

PERSONAS = {
    "agents": {
        "A01": {"label": "신입 상담원", "tenure_years": 0.3, "style": "친절하지만 매뉴얼이 몸에 덜 뱄다 — 위반 주입 대상", "tts_voice_hint": "여성, 20대, 밝은 톤", "say_voice": "Yuna"},
        "A02": {"label": "일반 상담원", "tenure_years": 2, "style": "매뉴얼 대체로 준수, 가끔 단정적 표현", "tts_voice_hint": "남성, 30대, 차분", "say_voice": "Reed"},
        "A03": {"label": "베테랑 상담원", "tenure_years": 7, "style": "매뉴얼 준수, 톤이 거의 변하지 않는다 — J-5 배정 대상", "tts_voice_hint": "여성, 40대, 낮고 일정", "say_voice": "Shelley"},
        # ↓ 2026-09-18 성격 다양화 — 응대 스타일이 갈리는 상담원. 매뉴얼에 «태도» 조항이 없어 A04 의 무뚝뚝함은 위반 라벨이 아니다
        "A04": {"label": "무뚝뚝·사무적 상담원", "tenure_years": 4, "style": "공감 표현 없이 짧게 끊어 말한다. 내용은 매뉴얼대로 — 태도 조항이 없어 위반 라벨 없음", "tts_voice_hint": "남성, 40대, 낮고 건조", "say_voice": "Reed"},
        "A05": {"label": "과잉 친절·단정형 상담원", "tenure_years": 1, "style": "말이 많고 「무조건」·「확실히」·「틀림없이」 로 단정한다 — C-1 반복 주입 대상, 지적받으면 바로 정정", "tts_voice_hint": "여성, 20대, 높고 빠름", "say_voice": "Sandy"},
        "A06": {"label": "외국어 응대 지향 상담원", "tenure_years": 3, "style": "쉬운 말·짧은 문장, 통역 지원을 먼저 안내한다. 요건은 줄이지도 늘리지도 않는다(TERM-1.5)", "tts_voice_hint": "여성, 30대, 또렷하고 느림", "say_voice": "Shelley"},
    },
    "customers": {
        "C01": {"label": "중국인 유학생", "korean": "중급", "temper": "밝음·간결", "say_voice": "Flo"},
        "C02": {"label": "베트남 출신 결혼이민자", "korean": "중급(조사 누락·짧은 문장)", "temper": "차분·조심스러움", "say_voice": "Sandy"},
        "C03": {"label": "내국인 직장인", "korean": "모국어", "temper": "급함·협조적", "say_voice": "Eddy"},
        "C04": {"label": "필리핀 출신 초보 부모", "korean": "초급(영어 혼용)", "temper": "밝음", "say_voice": "Flo"},
        "C05": {"label": "내국인 자영업자", "korean": "모국어", "temper": "다혈질 — 폭발 후 진정", "say_voice": "Rocko"},
        "C06": {"label": "반복 악성 민원인", "korean": "모국어", "temper": "모욕·성희롱·협박 반복 — 블랙리스트 후보", "say_voice": "Grandpa"},
        "C07": {"label": "내국인 재문의 민원인", "korean": "모국어", "temper": "욕설 없이 강하게 항의 — 톤만 튄다", "say_voice": "Sandy"},
        "C08": {"label": "내국인 70대 고령 세대원", "korean": "모국어", "temper": "지침·무기력 — 위기 신호", "say_voice": "Grandma"},
        "C09": {"label": "내국인 청년", "korean": "모국어", "temper": "무난", "say_voice": "Eddy"},
        # ↓ 2026-09-17 D-5 통화 온도용 — 한 통화 안에서 고객 발화가 8번 이상이어야 화자 기준선이 선다
        "C10": {"label": "평소엔 차분하다가 두 번 폭발하는 민원인", "korean": "모국어", "temper": "차분 → 폭발 → 진정 (두 번)", "say_voice": "Rocko"},
        "C11": {"label": "처음부터 끝까지 화가 난 민원인", "korean": "모국어", "temper": "통화 내내 높은 톤 — 기준선 자체가 높다", "say_voice": "Eddy"},
        "C12": {"label": "지친 고령 보호자", "korean": "모국어", "temper": "차분하다가 두 번 가라앉는다", "say_voice": "Grandma"},
        "C13": {"label": "차분한 민원인", "korean": "모국어", "temper": "끝까지 차분 — 대조군", "say_voice": "Sandy"},
        # ↓ 2026-09-18 성격 다양화. `tts_voice_hint` 의 「여성」·「남성」 은 Google TTS 음성 배분의 폴백 단서다
        "C14": {"label": "급한 직장인", "korean": "모국어", "temper": "재촉하고 말을 끊는다 — 욕설 없음", "tts_voice_hint": "남성, 30대, 빠름", "say_voice": "Eddy"},
        "C15": {"label": "의심 많은 민원인", "korean": "모국어", "temper": "같은 것을 세 번 확인한다 — 차분하지만 집요", "tts_voice_hint": "여성, 50대, 느리고 또박또박", "say_voice": "Shelley"},
        "C16": {"label": "일본 출신 초급 한국어 화자", "korean": "초급(일본어 단어 혼용·조사 누락)", "temper": "정중·조심스러움", "tts_voice_hint": "여성, 30대, 부드러움", "say_voice": "Flo"},
        "C17": {"label": "말이 옆길로 새는 고령 민원인", "korean": "모국어", "temper": "온화하고 말이 길다 — 본론에서 자꾸 벗어난다", "tts_voice_hint": "남성, 70대, 느림", "say_voice": "Grandpa"},
        "C18": {"label": "조용히 비꼬는 민원인", "korean": "모국어", "temper": "욕설 없이 비꼰다 — 톤은 끝까지 calm(C-6·D-5 대조군)", "tts_voice_hint": "여성, 40대, 낮고 건조", "say_voice": "Sandy"},
        "C19": {"label": "가족 대리인", "korean": "모국어", "temper": "협조적이지만 묻지 않은 개인정보를 줄줄 부른다 — P1·P2·P3 표본", "tts_voice_hint": "남성, 50대, 보통", "say_voice": "Rocko"},
    },
    "tones": {
        "calm": "기준 톤",
        "tense": "약간 빠르고 높음 (SSML 예: rate 105% · pitch +1st)",
        "raised": "목소리가 커짐 (rate 110% · pitch +3st · volume +4dB)",
        "shouting": "고함 (rate 115% · pitch +5st · volume +8dB)",
        "weary": "느리고 낮고 작음 (rate 85% · pitch -2st · volume -4dB)",
    },
}

# 대본 정의는 모듈 둘로 나눴다(2026-09-18) — 한 파일이 550줄을 넘겼다. 정본은 여전히 이 생성기다.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scenarios_v0_a import SCRIPTS as _SCRIPTS_A  # noqa: E402  SYN-001~014
from scenarios_v0_b import SCRIPTS as _SCRIPTS_B  # noqa: E402  SYN-015~024

SCRIPTS = _SCRIPTS_A + _SCRIPTS_B


def build(s):
    turns, errors = [], []
    pii_c, cg_c, comp = Counter(), Counter(), []
    tone_turns = []
    for i, (spk, text, tone, labels) in enumerate(s["turns"], 1):
        assert tone in PERSONAS["tones"], (s["id"], i, tone)
        t = {"seq": i, "speaker": spk, "text": text, "tone": tone}
        lab = {}
        for pat, span in labels.get("pii", []):
            if span not in text: errors.append(f"{s['id']}#{i} PII span 없음: {span}")
            lab.setdefault("pii", []).append({"pattern": pat, "span": span}); pii_c[pat] += 1
        for typ, phrase, alt in labels.get("compliance", []):
            if phrase not in text: errors.append(f"{s['id']}#{i} 위반 문구 없음: {phrase}")
            if spk != "agent": errors.append(f"{s['id']}#{i} 위반은 상담원 발화여야 함")
            lab.setdefault("compliance", []).append({"type": typ, "phrase": phrase, "expected_alternative_source": alt})
            comp.append({"seq": i, "type": typ})
        for typ, phrase in labels.get("call_guard", []):
            if phrase not in text: errors.append(f"{s['id']}#{i} 콜가드 문구 없음: {phrase}")
            if spk != "customer": errors.append(f"{s['id']}#{i} 콜가드는 고객 발화여야 함")
            lab.setdefault("call_guard", []).append({"type": typ, "phrase": phrase})
        for typ in {typ for typ, _ in labels.get("call_guard", [])}:
            cg_c[typ] += 1
        if turns and turns[-1]["speaker"] == spk:
            errors.append(f"{s['id']}#{i} 같은 화자가 연달아 말한다")
        if lab: t["labels"] = lab
        if spk == "customer" and tone != "calm": tone_turns.append({"seq": i, "tone": tone})
        turns.append(t)
    doc = {
        "id": s["id"], "version": "dasan-v0", "source": "synthetic", "generated_by": s.get("generated_by", GEN),
        "title": s["title"], "length_class": ("short" if len(turns) <= 9 else "medium" if len(turns) <= 19 else "long"), "turn_count": len(turns),
        "caller_number": s["caller_number"],
        "agent_persona": s["agent"], "customer_persona": s["customer"],
        "procedure": {"doc_ids": s["doc_ids"], "required_documents": s["required_documents"]},
        "turns": turns,
        "expected": {
            "pii_by_pattern": dict(sorted(pii_c.items())),
            "compliance": comp,
            "call_guard_by_type": dict(sorted(cg_c.items())),
            "customer_non_calm_turns": tone_turns,
            "call_temperature": {
                "customer_expected_outlier_turns": [t["seq"] for t in turns if t["speaker"] == "customer" and t["tone"] in ("shouting", "weary")],
                "customer_calm_turns": [t["seq"] for t in turns if t["speaker"] == "customer" and t["tone"] == "calm"],
                "customer_turns": sum(1 for t in turns if t["speaker"] == "customer"),
                "note": "의도한 연기(tts 운율 지시)에서 나온 기대값이다 — 측정값이 아니다. raised·tense 는 채점에서 뺀다",
            },
            "j": s["j"],
        },
        "notes": s["notes"],
    }
    return doc, errors


def main():
    all_err, docs = [], []
    for s in SCRIPTS:
        d, e = build(s); docs.append(d); all_err += e
    if all_err:
        print("\n".join(all_err)); sys.exit(1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "personas.json").write_text(json.dumps(PERSONAS, ensure_ascii=False, indent=2) + "\n")
    for d in docs:
        (OUT / f"{d['id']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    tot = Counter(); cg = Counter()
    for d in docs:
        tot.update(d["expected"]["pii_by_pattern"]); cg.update(d["expected"]["call_guard_by_type"])
        print(f"{d['id']} {d['length_class']:6} 턴 {d['turn_count']:2}  {d['agent_persona']}/{d['customer_persona']}  "
              f"PII {d['expected']['pii_by_pattern']}  위반 {[c['type'] for c in d['expected']['compliance']]}  "
              f"콜가드 {d['expected']['call_guard_by_type']}  톤변화 {len(d['expected']['customer_non_calm_turns'])}  "
              f"블랙리스트요청 {d['expected']['j']['blacklist_request']} 배정 {d['expected']['j']['routing']}")
    print("PII 합계", dict(sorted(tot.items())), "· 콜가드 합계", dict(cg))

main()
