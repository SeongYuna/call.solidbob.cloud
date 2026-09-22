# Requirement: A-3, C-5, C-6, F-2, D-1, SEC-1
"""합성 대본 한 건이 파이프라인을 **왕복**했는지 규칙으로 판정한다. 전부 순수 함수 — 스택 없이 pytest 로 돈다.

입력은 셋이다.
- 대본 JSON(`scripts/persona_sim/dasan-v0/SYN-*.json`) — 기대값(`expected`·턴 라벨)의 출처
- 대시보드가 읽는 API 응답 — `GET /hub/calls/{id}/transcript` 의 `segments`, `GET /hub/calls/{id}/record`
- DB 스냅샷(`e2e_check.py` 가 psycopg 로 뽑는다) — `transcript_segment`·`call_guard_flag`·`compliance_flag`·`closure`·`call`

판정은 «기대한 것이 나왔는가»만 본다. 나온 수치가 «좋은가»는 말하지 않는다 — 대본은 STT 를 거치지 않아 상한이고
(절대 원칙 10), 여기 나온 것은 `source: synthetic` 으로만 인용한다.

실패 원인 갈래(`cause`):
- `wiring`  배선 — 콜 미디에이터·서버 사이에서 빠진 호출·저장(예: 컴플라이언스 검사를 콜 미디에이터가 부르지 않는다)
- `rule`    규칙 — 마스킹·콜 가드·필요서류 규칙이 라벨을 못 잡았다(또는 과잉)
- `script`  대본 — 라벨·서류 이름이 규칙표와 다르게 적혔을 가능성
- `known`   알려진 미구현 — 미결에 이미 적혀 있는 것(통화 종료 상태 등). ❌ 로 세지 않고 ⚠ 로 남긴다
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from typing import Any

# 대본 → DB 의 갈래 이름은 같다(`call_guard_flag.category` CHECK). 컴플라이언스는 `C-1` ↔ `compliance_flag.rule_code` 도 같다.
CALL_GUARD_TYPES = ("insult", "threat", "sexual", "distress")

_SEPARATORS = re.compile(r"[\s\-.,()/]")


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    cause: str = ""          # wiring | rule | script | known | ""
    warn_only: bool = False  # True 면 ❌ 로 세지 않는다(known 전용)


@dataclass
class Verdict:
    script_id: str
    call_id: str
    checks: list[Check] = field(default_factory=list)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.ok and not c.warn_only]

    @property
    def warned(self) -> list[Check]:
        return [c for c in self.checks if not c.ok and c.warn_only]

    @property
    def ok(self) -> bool:
        return not self.failed


# ---------------------------------------------------------------- 대본 읽기

def labeled_pii(script: dict[str, Any]) -> list[tuple[int, str, str]]:
    """턴 라벨의 PII 값 — `(seq, pattern, span)`. 마스킹본 어디에도 남으면 안 되는 값이다."""
    out: list[tuple[int, str, str]] = []
    for turn in script.get("turns", []):
        for item in (turn.get("labels") or {}).get("pii", []) or []:
            out.append((int(turn["seq"]), str(item["pattern"]), str(item["span"])))
    return out


def labeled_call_guard(script: dict[str, Any]) -> set[tuple[int, str]]:
    """콜 가드 기대값 — «턴 × 갈래»(README 라벨 규칙: 한 턴에 같은 갈래 둘이어도 1)."""
    out: set[tuple[int, str]] = set()
    for turn in script.get("turns", []):
        for item in (turn.get("labels") or {}).get("call_guard", []) or []:
            out.add((int(turn["seq"]), str(item["type"])))
    return out


def labeled_compliance(script: dict[str, Any]) -> set[tuple[int, str]]:
    out: set[tuple[int, str]] = set()
    for turn in script.get("turns", []):
        for item in (turn.get("labels") or {}).get("compliance", []) or []:
            out.add((int(turn["seq"]), str(item["type"])))
    return out


# ---------------------------------------------------------------- 판정

def _squash(text: str) -> str:
    """구분자·공백을 뺀 형태 — 서버 마스킹 1단계와 같은 눈으로 본다(`010 0000 0104` 와 `01000000104` 는 같은 값)."""
    return _SEPARATORS.sub("", text)


def value_leaks(span: str, text: str) -> bool:
    """라벨 값이 마스킹본에 남아 있는가. 원형 그대로 또는 구분자를 뺀 형태로 찾는다."""
    if not span:
        return False
    if span in text:
        return True
    squashed = _squash(span)
    return len(squashed) >= 4 and squashed in _squash(text)


def leaked_chars(span: str, original: str, masked: str) -> str:
    """라벨 값의 **글자 중 하나라도** 마스킹본에 남았는가 — 남은 글자를 이어 돌려준다(없으면 "").

    `value_leaks` 는 값 **전체**가 남을 때만 잡는다. 2026-09-22 QA-4 에서 SYN-017#12 「다나카 유이」가 `*** *이` 로 나와
    ✅ 였다 — 마지막 글자 「이」가 남았는데도. C-5 는 누락 0건이 절대 규칙이라(절대 원칙 3·5) 한 글자라도 남으면 ❌ 다.

    대조 방법은 QA-4 스크립트와 같다 — 원문에서 라벨 값이 놓인 자리마다, 그 자리 글자가 마스킹본에서 가려졌는지 본다.
    공백·구분자(`-.,()/`)는 세지 않는다(가려도 안 가려도 값이 드러나지 않는다).
    - 서버 마스킹은 글자 수를 지키며 `*` 로 바꾼다(`server/apps/masking/domain/services/masker.py`) — 길이가 같으면 **자리 그대로** 대조한다
    - 길이가 다르면(다른 모양의 마스킹·자리 표시자) `SequenceMatcher` 로 원문 ↔ 마스킹본을 맞춰 **같다고 맞춰진 구간**에 든
      라벨 글자를 남은 것으로 본다. 우연히 같은 글자가 맞춰지면 과잉으로 잡을 수 있다 — 애매하면 잡는다(재현율 우선)
    """
    if not span or span not in original:
        return ""
    positions: set[int] = set()
    start = original.find(span)
    while start >= 0:
        positions.update(range(start, start + len(span)))
        start = original.find(span, start + 1)
    if len(original) == len(masked):
        kept = {i for i in positions if masked[i] == original[i]}
    else:
        kept = set()
        for tag, i1, i2, _j1, _j2 in SequenceMatcher(None, original, masked, autojunk=False).get_opcodes():
            if tag == "equal":
                kept.update(i for i in range(i1, i2) if i in positions)
    return "".join(original[i] for i in sorted(kept) if not _SEPARATORS.fullmatch(original[i]))


def judge_roundtrip(script: dict[str, Any], api_segments: list[dict[str, Any]], db_final_count: int | None) -> list[Check]:
    """자막 왕복 — 대본 턴 수 == API 확정 자막 수 == DB 확정 행 수, 화자 순서 일치."""
    turns = script.get("turns", [])
    finals = [s for s in api_segments if str(s.get("is_final")).lower() == "true"]
    # 턴(seq) == segment_id 전제(재생기가 턴마다 확정 하나) — 빠진 턴 번호를 적는다. 마지막 턴 유실(`w6-replay-last-turn`)이 바로 보이게
    got_ids = {int(s["segment_id"]) for s in finals}
    lost = [int(t["seq"]) for t in turns if int(t["seq"]) not in got_ids]
    checks = [
        Check("왕복·API 확정 자막 수", len(finals) == len(turns),
              f"대본 {len(turns)}턴 · API 확정 {len(finals)}건" + (f" · 빠진 턴 {lost}" if lost else ""), cause="wiring"),
    ]
    if db_final_count is not None:
        checks.append(Check("왕복·DB transcript_segment 행 수", db_final_count == len(turns),
                            f"대본 {len(turns)}턴 · DB {db_final_count}행", cause="wiring"))
    expected_speakers = [t["speaker"] for t in turns]
    got_speakers = [s.get("speaker") for s in sorted(finals, key=lambda s: int(s["segment_id"]))]
    checks.append(Check("왕복·화자 순서", got_speakers == expected_speakers,
                        "" if got_speakers == expected_speakers else f"기대 {expected_speakers} · 실제 {got_speakers}", cause="wiring"))
    return checks


def judge_sec1(script: dict[str, Any], api_segments: list[dict[str, Any]], db_texts: dict[int, str] | None) -> list[Check]:
    """SEC-1 — 라벨된 PII 값이 API 응답·DB 본문 어디에도 없다. 턴(seq)과 segment_id 는 같은 순번이다."""
    api_by_seq = {int(s["segment_id"]): str(s.get("text", "")) for s in api_segments if str(s.get("is_final")).lower() == "true"}
    leaks: list[str] = []
    for seq, pattern, span in labeled_pii(script):
        for where, texts in (("API", api_by_seq), ("DB", db_texts or {})):
            text = texts.get(seq)
            if text is None:
                continue
            if value_leaks(span, text):
                leaks.append(f"#{seq} {pattern} «{span}» {where} 본문에 남음")
    # 같은 값이 다른 턴에 그대로 반복되는 경우(이름을 두 번 부르는 등)도 잡는다 — 라벨은 첫 등장에만 붙어 있을 수 있다
    for _seq, pattern, span in labeled_pii(script):
        for seq2, text in api_by_seq.items():
            if value_leaks(span, text) and not any(f"#{seq2} {pattern} «{span}»" in leak for leak in leaks):
                leaks.append(f"#{seq2} {pattern} «{span}» API 본문에 남음(라벨은 다른 턴)")
    n = len(labeled_pii(script))
    return [Check("SEC-1·PII 원문 미잔존", not leaks,
                  f"라벨 {n}건 검사 · 누출 {len(leaks)}건" + (" — " + " / ".join(leaks) if leaks else ""), cause="rule"),
            judge_pii_chars(script, api_by_seq, db_texts)]


def judge_pii_chars(script: dict[str, Any], api_by_seq: dict[int, str], db_texts: dict[int, str] | None) -> Check:
    """C-5 — 라벨 값의 글자가 **하나라도** 가려지지 않고 남았는가(`leaked_chars`). 라벨이 붙은 턴과, 같은 값이 원문에
    다시 나오는 다른 턴을 API·DB 양쪽에서 본다. 턴(seq)과 segment_id 는 같은 순번이다(`judge_sec1` 과 같은 전제)."""
    originals = {int(t["seq"]): str(t.get("text", "")) for t in script.get("turns", [])}
    partial: list[str] = []
    for label_seq, pattern, span in labeled_pii(script):
        for seq, original in originals.items():
            if span not in original:
                continue
            for where, texts in (("API", api_by_seq), ("DB", db_texts or {})):
                masked = texts.get(seq)
                if masked is None:
                    continue
                left = leaked_chars(span, original, masked)
                if left:
                    other = "" if seq == label_seq else "(라벨은 다른 턴)"
                    partial.append(f"#{seq} {pattern} «{span}» → «{masked_window(span, original, masked)}» {where} 에 「{left}」 남음{other}")
    n = len(labeled_pii(script))
    return Check("C-5·PII 글자 단위 잔존 0", not partial,
                 f"라벨 {n}건 검사 · 글자가 남은 곳 {len(partial)}건" + (" — " + " / ".join(partial) if partial else ""),
                 cause="rule")


def masked_window(span: str, original: str, masked: str) -> str:
    """보고서에 보일 마스킹본 조각 — 길이가 같으면 라벨 자리를 그대로 잘라 보이고, 아니면 생략한다."""
    i = original.find(span)
    if i < 0 or len(original) != len(masked):
        return "…"
    return masked[i:i + len(span)]


def judge_call_guard(script: dict[str, Any], db_flags: list[tuple[int, str]]) -> list[Check]:
    """C-6 — DB `call_guard_flag` (segment_id, category) 를 «턴 × 갈래» 로 접어 라벨과 대조한다."""
    expected = labeled_call_guard(script)
    got = {(int(seg), str(cat)) for seg, cat in db_flags}
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    detail = f"기대 {len(expected)} · 탐지 {len(got)}"
    if missing:
        detail += " · 누락 " + ", ".join(f"#{s} {t}" for s, t in missing)
    if extra:
        detail += " · 과잉 " + ", ".join(f"#{s} {t}" for s, t in extra)
    return [Check("C-6·콜 가드 라벨 재현", not missing and not extra, detail, cause="rule")]


def judge_compliance(script: dict[str, Any], db_flags: list[tuple[int, str]]) -> list[Check]:
    """C-1~C-4 — DB `compliance_flag` (segment_id, rule_code) 대조. 라벨이 없는 대본은 «과잉 0» 만 본다."""
    expected = labeled_compliance(script)
    got = {(int(seg), str(code)) for seg, code in db_flags}
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    detail = f"기대 {len(expected)} · 탐지 {len(got)}"
    if missing:
        detail += " · 누락 " + ", ".join(f"#{s} {t}" for s, t in missing)
    if extra:
        detail += " · 과잉 " + ", ".join(f"#{s} {t}" for s, t in extra)
    # 탐지가 0 이고 기대가 있으면 배선(콜 미디에이터가 검사를 안 부름)이 첫 가설이다 — 규칙이 전부 놓칠 확률보다 크다
    cause = "wiring" if expected and not got else "rule"
    return [Check("C-1~C-4·컴플라이언스 라벨 재현", not missing and not extra, detail, cause=cause)]


_PAREN = re.compile(r"\s*\([^)]*\)")


def doc_name(name: str) -> str:
    """서류 이름 대조용 — 괄호 부연(`신분증(외국인등록증 인정)`)을 뗀다. 규칙표는 부연 없이 적는다."""
    return _PAREN.sub("", str(name)).strip()


def _clause_number(doc_id: str) -> str:
    """`DASAN-TERM-4.18` → `4.18`. 카드 제목이 `4.18 도서관 회원 가입 — …` 로 시작한다."""
    return doc_id.rsplit("-", 1)[-1]


def judge_required_docs(script: dict[str, Any], record: dict[str, Any]) -> list[Check]:
    """F-2 — `/record.closures` 에 대본 절차의 판정이 있고, 마지막 판정의 서류 목록이 대본과 같은가.
    추천 카드(B) 에 그 절차 조항이 한 번이라도 떴는가. 끝에 대본 절차 **밖** 판정이 없는가(`judge_foreign_procedures`)."""
    procedure = script.get("procedure") or {}
    doc_ids = [d for d in procedure.get("doc_ids", []) if "-TERM-" in d]
    expected_docs = [doc_name(d) for d in procedure.get("required_documents", [])]
    closures = [c for c in record.get("closures", []) if c.get("procedure") in doc_ids]
    checks: list[Check] = []

    if not expected_docs:
        # 소관 아님·필요서류 없음 대본 — 판정이 없어야 맞다
        checks.append(Check("F-2·필요서류 없음(판정 0건)", not closures,
                            f"대본 서류 0 · 판정 {len(closures)}건", cause="rule"))
        checks.append(judge_foreign_procedures(script, record))
        return checks

    checks.append(Check("F-2·절차 판정 존재", bool(closures),
                        f"절차 {doc_ids} · 판정 {len(closures)}건" + ("" if closures else f" — 저장된 절차: {sorted({c.get('procedure') for c in record.get('closures', [])})}"),
                        cause="wiring"))
    if closures:
        last = max(closures, key=lambda c: int(c.get("closure_id", 0)))
        got_docs = [doc_name(i.get("document_name", "")) for i in last.get("items", [])]
        missing = [d for d in expected_docs if d not in got_docs]
        extra = [d for d in got_docs if d not in expected_docs]
        detail = f"대본 {expected_docs} · 규칙표 {got_docs}"
        if missing or extra:
            detail += f" · 대본에만 {missing} · 규칙표에만 {extra} (조건부 서류를 대본이 필수로 적었는지 먼저 본다)"
        checks.append(Check("F-2·서류 목록 일치", not missing and not extra, detail, cause="script"))
        informed_all = all(str(i.get("informed")).lower() == "true" for i in last.get("items", []))
        checks.append(Check("F-2·마지막 판정 complete", str(last.get("verdict")) == "complete" and informed_all,
                            f"verdict={last.get('verdict')} · 안내됨 {[i.get('document_name') for i in last.get('items', []) if str(i.get('informed')).lower() == 'true']}",
                            cause="rule"))

    cards = [c for r in record.get("recommendations", []) for c in r.get("cards", [])]
    card_docs = {c.get("source_doc_id") for c in cards if c.get("source_doc_id")}
    hit = [d for d in doc_ids if d in card_docs]
    loose = ""
    if not hit and cards:
        # `source_doc_id` 가 비어 있으면 제목 앞 조항 번호로 느슨하게 본다(TERM·MANUAL 번호가 겹칠 수 있다 — 상한)
        titles = [str(c.get("title", "")) for c in cards]
        hit = [d for d in doc_ids if any(t.startswith(_clause_number(d) + " ") for t in titles)]
        loose = " · source_doc_id 없음 — 제목 번호로 대조"
    checks.append(Check("B·필요서류 카드 노출", bool(hit),
                        f"절차 {doc_ids} · 카드에 뜬 것 {hit} (추천 {len(record.get('recommendations', []))}회 · 카드 {len(cards)}장){loose}", cause="rule"))
    if cards:
        checks.append(Check("B-6·카드 근거 조항 저장(source_doc_id)", bool(card_docs),
                            f"카드 {len(cards)}장 중 source_doc_id 있는 것 {sum(1 for c in cards if c.get('source_doc_id'))}장 — `document` 테이블이 비어 FK 를 못 채우는 것으로 보인다",
                            cause="wiring", warn_only=True))
    checks.append(judge_foreign_procedures(script, record))
    return checks


def judge_foreign_procedures(script: dict[str, Any], record: dict[str, Any]) -> Check:
    """F-2 — 대본 절차(`procedure.doc_ids`) **밖**의 절차로 낸 판정이 없어야 한다.

    전에는 대본 절차의 판정만 골라 봐서, 엉뚱한 절차의 「빠진 서류」가 상담원 화면에 떠도 ✅ 였다 — 2026-09-22 운영 SYN-010
    (고속버스 예매 취소, 서류 없음)이 `TERM-2.9 대중교통 분실물 수령` `incomplete` 를 냈는데 E2E 는 통과였다.
    서류 없는 대본이면 대본 절차 안의 판정은 `F-2·필요서류 없음` 이 따로 본다 — 둘을 합치면 «판정이 하나라도 있으면 ❌» 다.
    """
    procedure = script.get("procedure") or {}
    allowed = set(procedure.get("doc_ids", []))
    foreign = [c for c in record.get("closures", []) if c.get("procedure") not in allowed]
    by_procedure: dict[str, list[str]] = {}
    for c in sorted(foreign, key=lambda c: int(c.get("closure_id", 0) or 0)):
        by_procedure.setdefault(str(c.get("procedure")), []).append(str(c.get("verdict")))
    listed = " / ".join(f"{proc} {'·'.join(verdicts)}" for proc, verdicts in sorted(by_procedure.items()))
    return Check("F-2·엉뚱한 절차 판정 0건", not foreign,
                 f"대본 절차 {sorted(allowed)} 밖 판정 {len(foreign)}건" + (f" — {listed}" if listed else ""),
                 cause="rule")


def judge_postcall(record: dict[str, Any], call_row: dict[str, Any] | None) -> list[Check]:
    """D-1 — 통화 후 요약 초안이 DB 에 있고 `/record` 로 읽힌다. 통화 종료 상태는 알려진 미구현(⚠)."""
    checks = [
        Check("D-1·요약 초안 저장", bool(str(record.get("summary_text") or "").strip()),
              f"요약 {len(str(record.get('summary_text') or ''))}자 · 유형 {record.get('inquiry_type')}", cause="wiring"),
        # D-2 — 못 가르면 「미분류」가 와야 한다. NULL 은 `/close` 가 유형을 저장하지 않았다는 뜻이다(w6-d2-inquiry-type-null)
        Check("D-2·문의 유형 저장", bool(str(record.get("inquiry_type") or "").strip()),
              f"inquiry_type={record.get('inquiry_type')}", cause="wiring"),
        Check("통화 후·call 행 존재", call_row is not None, "" if call_row else "call 테이블에 행이 없다", cause="wiring"),
    ]
    if call_row is not None:
        checks.append(Check("통화 후·stt_engine=synthetic-script", call_row.get("stt_engine") == "synthetic-script",
                            f"stt_engine={call_row.get('stt_engine')}", cause="wiring"))
        checks.append(Check("통화 후·customer_id 연결(발신 번호)", call_row.get("customer_id") is not None,
                            "" if call_row.get("customer_id") else "customer_id NULL — X-Caller-Phone·CUSTOMER_REF_HMAC_KEY 확인",
                            cause="wiring"))
        ended = call_row.get("ended_at") is not None and call_row.get("status") != "in_progress"
        checks.append(Check("통화 후·ended_at/status 갱신", ended,
                            f"status={call_row.get('status')} · ended_at={'있음' if call_row.get('ended_at') else 'NULL'} — `/close` 가 종료 상태를 바꾸지 않는다(2026-09-17 미결)",
                            cause="known", warn_only=True))
    return checks


def judge(script: dict[str, Any], call_id: str, api_segments: list[dict[str, Any]], record: dict[str, Any],
          db: dict[str, Any]) -> Verdict:
    """`db` 키: `final_texts: {segment_id: text}` · `call_guard: [(segment_id, category)]` ·
    `compliance: [(segment_id, rule_code)]` · `call: {...} | None`. 없는 키는 그 판정을 건너뛴다."""
    v = Verdict(script_id=str(script.get("id")), call_id=call_id)
    final_texts = db.get("final_texts")
    v.checks += judge_roundtrip(script, api_segments, len(final_texts) if final_texts is not None else None)
    v.checks += judge_sec1(script, api_segments, final_texts)
    if "call_guard" in db:
        v.checks += judge_call_guard(script, db["call_guard"])
    if "compliance" in db:
        v.checks += judge_compliance(script, db["compliance"])
    v.checks += judge_required_docs(script, record)
    v.checks += judge_postcall(record, db.get("call"))
    return v
