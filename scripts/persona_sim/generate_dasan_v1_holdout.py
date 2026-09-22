# Requirement: B-1, B-3, F-2, C-5
"""합성 통화 보류 표본 dasan-v1-holdout 생성·검증 (`decisions/219`).

    python3 scripts/persona_sim/generate_dasan_v1_holdout.py

`generate_dasan_v0.py` 와 같은 JSON 모양·같은 검사(라벨 문구가 발화에 글자 그대로 있는가 · 같은 화자가 연달아 말하지 않는가)에
**가짜 개인정보 검사**를 더했다 — 전화 `010-0000-XXXX`(한글 수사 포함) · 주민번호 체크섬 불통과 · 카드 Luhn 불통과 ·
계좌 `000000…` · 주소 「한별시」. 하나라도 어기면 쓰지 않고 멈춘다. 페르소나는 `dasan-v0/personas.json` 것을 그대로 쓴다
(재생기가 거기서 읽는다) — 여기서 새로 만들지 않는다.

v0 생성기를 import 하지 않는 이유: 그 파일은 import 만 해도 `main()` 이 돌아 v0 JSON 을 다시 쓴다.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "dasan-v1-holdout"
VERSION = "dasan-v1-holdout"
TONES = ("calm", "tense", "raised", "shouting", "weary")

sys.path.insert(0, str(HERE))
from scenarios_v1_holdout import GEN_V1, SCRIPTS  # noqa: E402

_SINO = {"공": "0", "영": "0", "일": "1", "이": "2", "삼": "3", "사": "4", "오": "5", "육": "6", "칠": "7", "팔": "8", "구": "9"}


def _digits(span: str) -> str:
    return "".join(_SINO.get(ch, ch) for ch in span if ch.isdigit() or ch in _SINO)


def _luhn_ok(num: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(num)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
    return total % 10 == 0


def _rrn_checksum_ok(num: str) -> bool:
    weights = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)
    s = sum(int(num[i]) * weights[i] for i in range(12))
    return (11 - s % 11) % 10 == int(num[12])


def fake_pii_errors(pattern: str, span: str) -> list[str]:
    """가짜 값 규칙(README 「데이터 취급」)을 어기면 이유를 돌려준다."""
    d = _digits(span)
    if pattern == "P1" and (len(d) != 13 or _rrn_checksum_ok(d) or not d.endswith("000000")):
        return [f"P1 주민번호는 13자리·체크섬 불통과·뒷자리 000000 이어야 한다: {span}"]
    if pattern == "P2" and (len(d) != 16 or _luhn_ok(d)):
        return [f"P2 카드번호는 16자리·Luhn 불통과여야 한다: {span}"]
    if pattern == "P3" and not d.startswith("000000"):
        return [f"P3 계좌는 000000 으로 시작해야 한다: {span}"]
    if pattern == "P4" and not d.startswith("0100000"):
        return [f"P4 전화는 010-0000-XXXX 여야 한다: {span}"]
    if pattern == "P7" and not span.startswith("한별시"):
        return [f"P7 주소는 가상 지자체 「한별시」여야 한다: {span}"]
    return []


def build(s):
    turns, errors = [], []
    pii_c, comp = Counter(), []
    tone_turns = []
    for i, (spk, text, tone, labels) in enumerate(s["turns"], 1):
        if tone not in TONES:
            errors.append(f"{s['id']}#{i} 톤 이름: {tone}")
        t = {"seq": i, "speaker": spk, "text": text, "tone": tone}
        lab = {}
        for pat, span in labels.get("pii", []):
            if span not in text:
                errors.append(f"{s['id']}#{i} PII span 없음: {span}")
            errors += [f"{s['id']}#{i} {e}" for e in fake_pii_errors(pat, span)]
            lab.setdefault("pii", []).append({"pattern": pat, "span": span})
            pii_c[pat] += 1
        for typ, phrase, alt in labels.get("compliance", []):
            if phrase not in text:
                errors.append(f"{s['id']}#{i} 위반 문구 없음: {phrase}")
            if spk != "agent":
                errors.append(f"{s['id']}#{i} 위반은 상담원 발화여야 함")
            lab.setdefault("compliance", []).append({"type": typ, "phrase": phrase, "expected_alternative_source": alt})
            comp.append({"seq": i, "type": typ})
        if labels.get("call_guard"):
            errors.append(f"{s['id']}#{i} 보류 표본에는 콜 가드 라벨을 넣지 않는다(절차 채택 표본이다)")
        if turns and turns[-1]["speaker"] == spk:
            errors.append(f"{s['id']}#{i} 같은 화자가 연달아 말한다")
        # 라벨 밖 숫자열도 가짜 규칙을 지키는가 — 010 으로 시작하는 번호는 전부 010-0000
        for m in re.finditer(r"010[\s-]?\d{4}[\s-]?\d{4}", text):
            if not _digits(m.group()).startswith("0100000"):
                errors.append(f"{s['id']}#{i} 실존할 수 있는 전화번호: {m.group()}")
        if lab:
            t["labels"] = lab
        if spk == "customer" and tone != "calm":
            tone_turns.append({"seq": i, "tone": tone})
        turns.append(t)
    if not s["caller_number"].startswith("0100000"):
        errors.append(f"{s['id']} 발신 번호는 010-0000-XXXX 여야 한다")
    if s["required_documents"] and not any("-TERM-" in d for d in s["doc_ids"]):
        errors.append(f"{s['id']} 서류가 있는 대본은 TERM 조항이 doc_ids 에 있어야 한다")
    doc = {
        "id": s["id"], "version": VERSION, "source": "synthetic", "generated_by": s.get("generated_by", GEN_V1),
        "title": s["title"],
        "length_class": ("short" if len(turns) <= 9 else "medium" if len(turns) <= 19 else "long"),
        "turn_count": len(turns),
        "caller_number": s["caller_number"],
        "agent_persona": s["agent"], "customer_persona": s["customer"],
        "procedure": {"doc_ids": s["doc_ids"], "required_documents": s["required_documents"],
                      **({"conditional_documents": s["conditional_documents"]} if s.get("conditional_documents") else {})},
        "turns": turns,
        "expected": {
            "pii_by_pattern": dict(sorted(pii_c.items())),
            "compliance": comp,
            "call_guard_by_type": {},
            "customer_non_calm_turns": tone_turns,
            "j": s["j"],
        },
        "notes": s["notes"],
    }
    return doc, errors


def check_personas(docs) -> list[str]:
    personas = json.loads((HERE / "dasan-v0" / "personas.json").read_text(encoding="utf-8"))
    known = set(personas["agents"]) | set(personas["customers"])
    return [f"{d['id']} 페르소나 없음: {p}" for d in docs for p in (d["agent_persona"], d["customer_persona"]) if p not in known]


def main() -> int:
    all_err, docs = [], []
    ids = [s["id"] for s in SCRIPTS]
    if len(set(ids)) != len(ids):
        all_err.append(f"대본 ID 가 겹친다: {ids}")
    for s in SCRIPTS:
        d, e = build(s)
        docs.append(d)
        all_err += e
    all_err += check_personas(docs)
    if all_err:
        print("\n".join(all_err))
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for d in docs:
        (OUT / f"{d['id']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for d in docs:
        rule_proc = [x for x in d["procedure"]["doc_ids"] if "-TERM-" in x]
        print(f"{d['id']} {d['length_class']:6} 턴 {d['turn_count']:2}  {d['agent_persona']}/{d['customer_persona']}  "
              f"서류 {len(d['procedure']['required_documents'])}  TERM {rule_proc}  PII {d['expected']['pii_by_pattern']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
