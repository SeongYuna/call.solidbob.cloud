# Requirement: D-1, D-2
"""통화 후 초안의 규칙 부분 — D-2 유형 제안 · D-1 모델 요약 검사. 순수 파이썬(`ai/.importlinter` 계약 3).

모듈 이름이 `postcall` 이 아닌 이유: `server/apps/postcall`(규칙 발췌 초안, `decisions/306`)과 경로가 겹친다(`pii_ner` 와 같은 사정).

## D-2 — 검색 결과의 장(章) 투표로 **제안**한다

지식베이스 TERM 의 장 구성이 AI Hub 「민원(콜센터) 질의응답」 다산콜센터 카테고리를 그대로 따라 쓰였다(TERM.md 머리말). 그래서
고객 발화로 검색한 상위 조항들의 **장 번호를 순위 가중치로 투표**해 유형을 고른다. 모델이 유형을 «판정» 하지 않는다(절대 원칙 9) —
검색이 조항을 고르고, 장→유형 대응은 표로 고정한다. **결과는 제안이다**(`CallSummaryDraft.inquiry_type`, 상담원이 확정).

- 1장(총칙)·MANUAL·POLICY 조항은 투표에서 뺀다 — 어느 유형에도 속하지 않는다
- 6장(재난·생계 지원금)은 AI Hub 카테고리에 없다 → **투표에서 뺀다.** 억지로 「일반행정」에 넣으면 지어낸 대응이다
- 표가 하나도 없으면 `None` — 없는 근거로 유형을 만들지 않는다(`decisions/306` 이 D-2 를 None 으로 둔 이유와 같다)

## D-1 — 모델 요약을 규칙으로 검사한다

요약은 설명이라 모델에게 맡기되, **화면에 싣기 전에** 검사한다. 하나라도 걸리면 규칙 발췌 초안으로 내려간다:
- **숫자** — 요약에 나온 숫자 덩어리가 자막에 없으면 지어낸 것이다(금액·날짜·번호)
- **가림 문자** — 자막의 `*` 가 요약에서 사라지고 그 자리에 무엇이 들어갔는지 알 수 없으므로, 요약에 한글 이름·주소처럼 보이는 새 고유명사가 있는지는
  규칙으로 못 잡는다. 대신 **요약에 `*` 를 풀어 쓴 숫자가 들어갈 수 없게** 숫자 검사가 막는다(SEC-1)
- **금지 표현** — 부록 A-1(판정·점수·보장)
- **길이** — 비었거나 너무 길면 요약이 아니다
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

# TERM 장 번호 → AI Hub 다산콜센터 카테고리(= 유형 제안 값). 표 밖의 장은 투표하지 않는다
CHAPTER_TO_TYPE: dict[int, str] = {
    2: "대중교통 안내",
    3: "생활하수도 관련 문의",
    4: "일반행정 문의",
    5: "코로나19 관련 상담",
}
INQUIRY_TYPES: tuple[str, ...] = tuple(CHAPTER_TO_TYPE.values())

_TERM_ID = re.compile(r"^[A-Z]+-TERM-(\d+)\.\d+")


def suggest_inquiry_type(ranked_doc_ids: Iterable[str]) -> str | None:
    """순위대로 받은 조항 ID → 유형 제안. 가중치는 1/순위(1위가 가장 크다). 동점이면 표 순서가 앞선 쪽."""
    votes: dict[str, float] = defaultdict(float)
    for rank, doc_id in enumerate(ranked_doc_ids, start=1):
        m = _TERM_ID.match(doc_id)
        if not m:
            continue
        kind = CHAPTER_TO_TYPE.get(int(m.group(1)))
        if kind:
            votes[kind] += 1 / rank
    if not votes:
        return None
    return max(INQUIRY_TYPES, key=lambda k: (votes.get(k, 0.0), -INQUIRY_TYPES.index(k)))


FORBIDDEN_TERMS = ("안전합니다", "위험도", "등급", "점수", "%", "확실", "무조건", "보장", "틀림없")
SUMMARY_MAX_CHARS = 300
_DIGITS = re.compile(r"\d[\d,.]*\d|\d")


def summary_problems(summary: str, transcript: str) -> list[str]:
    """모델 요약이 화면에 나가면 안 되는 이유 목록. 비면 통과."""
    problems: list[str] = []
    text = summary.strip()
    if not text:
        return ["빈 요약"]
    if len(text) > SUMMARY_MAX_CHARS:
        problems.append(f"길이 {len(text)}자 > {SUMMARY_MAX_CHARS}")
    src_digits = {d.replace(",", "") for d in _DIGITS.findall(transcript)}
    for d in _DIGITS.findall(text):
        if d.replace(",", "") not in src_digits:
            problems.append(f"자막에 없는 숫자 {d}")
    for t in FORBIDDEN_TERMS:
        if t in text:
            problems.append(f"금지 표현 {t}")
    return problems


SYSTEM_PROMPT = (
    "민원 상담 통화의 전사를 상담원이 확인할 요약 초안으로 두세 문장에 정리한다. "
    "고객이 무엇을 문의했고 상담원이 무엇을 안내했는지만 쓴다. 전사에 없는 사실·숫자·이름을 쓰지 않는다. "
    "*로 가려진 부분은 추측하지 않는다. 판단·평가·점수를 쓰지 않는다."
)


def build_messages(lines: list[tuple[str, str]]) -> list[dict[str, str]]:
    """(화자, 마스킹 자막) 목록 → 채팅 메시지. 자막은 **마스킹본**이어야 한다(SEC-1, `PostcallPort` 계약)."""
    who = {"customer": "고객", "agent": "상담원"}
    transcript = "\n".join(f"{who.get(s, s)}: {t}" for s, t in lines)
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"전사:\n{transcript}\n\n요약:"}]
