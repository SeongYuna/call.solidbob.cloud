# Requirement: D-1, D-2, D-3
"""통화 후 처리 초안 — **규칙 기반 발췌다. 생성 모델은 여기 없다** (`decisions/306`).

요약을 «쓰는» 것이 아니라 마스킹된 확정 발화에서 **골라 붙인다.** 지어낸 문장이 없으니 환각이 없고,
화면에 나간 글자는 전부 자막 어딘가에 있다. LLM 요약(런북 14장 Ollama+EXAONE)이 운영에 올라오면
같은 포트 뒤에 갈아 끼운다 — 이 파일은 그때도 폴백으로 남길 수 있다.

- D-1 요약: 고객의 첫 «실질» 발화(문의) + 그 뒤 상담원의 첫 «실질» 발화(안내) + 발화 건수
- D-2 유형: 지식베이스 장 어휘로 **제안**한다(`inquiry_rules.py`, `decisions/323`). 안 걸리면 「미분류」.
  ~~만들지 않는다(None) — 유형을 가를 규칙표가 없다~~ 가 09-22 까지의 판단이었다(운영 24/24 NULL)
- D-3 후속조치: 상담원이 「…해 드리겠습니다」 로 **약속한** 발화 중 연락·발송·접수 류 동사가 있는 것

⚠ **한계 — 주장 범위를 넘지 않는다.**
- «실질» 발화는 공백 뺀 길이로만 가른다(`MIN_SUBSTANTIVE_CHARS`). 「여보세요」·「네」 는 빠지지만
  짧은 핵심 발화(「카드 분실요」)도 빠질 수 있다
- 후속조치는 어휘 규칙이라 「연락 안 드리겠습니다」 같은 부정도 잡는다 — 초안이고 상담원이 지운다
- 품질을 잰 적이 없다(골든셋 D 케이스 0건). **측정 전까지 요약 품질을 수치로 말하지 않는다**
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MIN_SUBSTANTIVE_CHARS = 8  # 공백 뺀 글자 수. 인사·맞장구를 거르는 선
EXCERPT_MAX_CHARS = 100  # 요약에 싣는 발화 하나의 최대 길이
ACTION_MAX_CHARS = 200  # db `follow_up_action.action_text` VARCHAR(200)

# 「…해 드리겠습니다」 류 약속 어미. 공백을 뺀 문자열에 건다(「보내 드리겠습니다」·「보내드리겠습니다」 전사 차이)
_PROMISE = re.compile(r"(드리겠습니다|드릴게요|드릴께요|드리도록하겠습니다)")
# 통화가 끝난 뒤에도 할 일이 남는 동작. 「도와드리겠습니다」 처럼 통화 안에서 끝나는 말은 넣지 않는다
_FOLLOW_UP_VERBS = ("연락", "회신", "전화", "문자", "발송", "보내", "접수", "전달", "연결", "처리", "확인해")
# 서류를 안내한 상담원 발화를 고르는 어휘(2026-09-23). 채점에서 「서류」 항목이 23건 중 2건만 잡혔다(`decisions/218`) —
# 요약이 「첫 문의 + 첫 안내」 두 줄뿐이라 **중·후반의 서류 안내를 통째로 버렸기** 때문이다. 지어내지 않고 그 줄을 더 싣는다.
_DOC_WORDS = ("서류", "신분증", "증명서", "등본", "초본", "신고서", "확인서", "위임장", "원본", "사본",
              "여권", "등록증", "면허증", "도장", "인감", "통장", "영수증", "진단서", "계약서", "지참", "가져오")
MAX_DOC_EXCERPTS = 3  # 서류 안내는 여러 줄에 걸쳐 나온다 — 너무 길어지지 않게 셋까지
MAX_ACTION_EXCERPTS = 5  # 요약에 싣는 후속 조치 수. 전체 목록은 `follow_up_actions` 에 그대로 남는다


@dataclass(frozen=True)
class Utterance:
    speaker: str  # "customer" | "agent"
    text: str  # 마스킹 완료본 (SEC-1)


@dataclass(frozen=True)
class DraftParts:
    summary_text: str
    inquiry_type: str | None
    follow_up_actions: tuple[str, ...]


def _squash(text: str) -> str:
    return "".join(text.split())


def _substantive(u: Utterance) -> bool:
    return len(_squash(u.text)) >= MIN_SUBSTANTIVE_CHARS


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _doc_excerpts(utterances: list[Utterance], *, skip: set[int]) -> list[str]:
    """서류를 안내한 **상담원** 발화. 순서대로, 중복 없이, `MAX_DOC_EXCERPTS` 까지."""
    picked: list[str] = []
    for i, u in enumerate(utterances):
        if i in skip or u.speaker != "agent" or not _substantive(u):
            continue
        if any(word in _squash(u.text) for word in _DOC_WORDS):
            text = _clip(u.text, EXCERPT_MAX_CHARS)
            if text not in picked:
                picked.append(text)
            if len(picked) == MAX_DOC_EXCERPTS:
                break
    return picked


def _summary(utterances: list[Utterance], follow_ups: tuple[str, ...]) -> str:
    customer_count = sum(1 for u in utterances if u.speaker == "customer")
    agent_count = sum(1 for u in utterances if u.speaker == "agent")

    parts: list[str] = []
    used: set[int] = set()
    inquiry_at = next(
        (i for i, u in enumerate(utterances) if u.speaker == "customer" and _substantive(u)), None
    )
    if inquiry_at is not None:
        used.add(inquiry_at)
        parts.append(f"고객 문의: {_clip(utterances[inquiry_at].text, EXCERPT_MAX_CHARS)}")
        answer_at = next(
            (i for i, u in enumerate(utterances) if i > inquiry_at and u.speaker == "agent" and _substantive(u)),
            None,
        )
        if answer_at is not None:
            used.add(answer_at)
            parts.append(f"상담원 안내: {_clip(utterances[answer_at].text, EXCERPT_MAX_CHARS)}")

    # 2026-09-23 세 줄을 더 싣는다 — 전부 **자막에 있는 문장 그대로**다(발췌 원칙, `decisions/306`).
    docs = _doc_excerpts(utterances, skip=used)
    if docs:
        parts.append("필요서류 안내: " + " · ".join(docs))
    if follow_ups:
        # 후속 조치는 이미 따로 뽑아 저장한다(D-3). 요약에도 실어야 통화 기록 한 줄만 봐도 「무엇을 해 주기로 했는지」가 보인다
        parts.append("후속 조치: " + " · ".join(_clip(a, EXCERPT_MAX_CHARS) for a in follow_ups[:MAX_ACTION_EXCERPTS]))
    closing_at = next(
        (i for i in range(len(utterances) - 1, -1, -1)
         if i not in used and utterances[i].speaker == "agent" and _substantive(utterances[i])),
        None,
    )
    if closing_at is not None and closing_at > (inquiry_at or 0):
        parts.append(f"마무리 안내: {_clip(utterances[closing_at].text, EXCERPT_MAX_CHARS)}")

    # 발췌할 발화가 없어도 빈 요약을 내지 않는다 — 건수는 사실이다
    parts.append(f"발화 고객 {customer_count}건 · 상담원 {agent_count}건 (규칙 발췌 초안)")
    return " / ".join(parts)


def _follow_ups(utterances: list[Utterance]) -> tuple[str, ...]:
    actions: list[str] = []
    for u in utterances:
        if u.speaker != "agent":
            continue
        squashed = _squash(u.text)
        if _PROMISE.search(squashed) and any(verb in squashed for verb in _FOLLOW_UP_VERBS):
            action = _clip(u.text, ACTION_MAX_CHARS)
            if action not in actions:
                actions.append(action)
    return tuple(actions)


def build_draft(utterances: list[Utterance]) -> DraftParts:
    """발화 순서대로 받은 확정 발화 → 초안 조각. 순서는 호출자가 맞춘다(segment_id 오름차순)."""
    from .inquiry_rules import classify_inquiry  # noqa: PLC0415 — inquiry_rules 가 Utterance 를 여기서 가져간다

    follow_ups = _follow_ups(utterances)
    return DraftParts(
        summary_text=_summary(utterances, follow_ups),
        inquiry_type=classify_inquiry(utterances),
        follow_up_actions=follow_ups,
    )
