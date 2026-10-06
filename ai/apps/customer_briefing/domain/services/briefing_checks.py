# Requirement: F-3
"""모델 브리핑의 프롬프트와 **출력 검사** — 순수 파이썬(`ai/.importlinter` 계약 3). 판정은 하지 않는다(`decisions/220` 2절).

검사에 하나라도 걸리면 규칙 브리핑으로 내려간다(어댑터 몫).
"""

from __future__ import annotations

import re
from datetime import timedelta, timezone

from hub.app.dtos.customer_briefing_dto import BRIEFING_PURPOSES, BriefingFacts

_KST = timezone(timedelta(hours=9))
FORBIDDEN_TERMS = ("안전합니다", "위험", "등급", "점수", "%", "확실", "무조건", "보장", "틀림없", "요주의")
PURPOSE_MAX_CHARS = 120
LINE_MAX_CHARS = 90
_DIGITS = re.compile(r"\d+")

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(BRIEFING_PURPOSES)},
        "purpose": {"type": "string"},
        "lines": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
    },
    "required": ["category", "purpose", "lines"],
}

SYSTEM_PROMPT = (
    "상담원이 전화를 받기 전에 읽을 고객 브리핑을 쓴다. 아래 '지난 통화 사실'만 근거로 쓰고 없는 사실·숫자·이름을 만들지 않는다. "
    "이번 통화의 목적을 다음 중 하나로 추정한다: " + ", ".join(BRIEFING_PURPOSES) + ". "
    "purpose 는 '~로 보입니다'로 끝나는 한 문장, lines 는 상담원이 3초 안에 읽을 짧은 줄 세 개 이하다. "
    "평가·점수·단정(위험, 요주의 등)을 쓰지 않는다. *로 가려진 부분은 추측하지 않는다."
)


def render_facts(facts: BriefingFacts) -> str:
    out = []
    for i, c in enumerate(facts.prior_calls, start=1):
        day = c.started_at.astimezone(_KST).strftime("%m-%d")
        out.append(f"[지난 통화 {i}] {day} · 유형 {c.inquiry_type or '미정'} · 요약 {c.summary_text or '없음'}")
        if c.open_follow_ups:
            out.append("  후속조치: " + "; ".join(c.open_follow_ups))
        if c.incomplete_procedures:
            out.append("  서류 안내 미완료 절차: " + ", ".join(c.incomplete_procedures))
        if c.call_guard_categories:
            out.append("  고객 쪽 신호: " + ", ".join(c.call_guard_categories))
    if facts.blacklisted:
        out.append("블랙리스트 적용 중")
    return "\n".join(out)


def build_messages(facts: BriefingFacts) -> list[dict[str, str]]:
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "지난 통화 사실:\n" + render_facts(facts)}]


def briefing_problems(category: str, purpose: str, lines: list[str], source_text: str) -> list[str]:
    problems: list[str] = []
    if category not in BRIEFING_PURPOSES:
        problems.append(f"목록 밖 범주 {category}")
    if not purpose.strip():
        problems.append("빈 목적")
    if len(purpose) > PURPOSE_MAX_CHARS:
        problems.append(f"목적 길이 {len(purpose)}자")
    if not 1 <= len(lines) <= 3:
        problems.append(f"줄 수 {len(lines)}")
    for line in lines:
        if len(line) > LINE_MAX_CHARS:
            problems.append(f"줄 길이 {len(line)}자")
    src_digits = set(_DIGITS.findall(source_text))
    for d in _DIGITS.findall(" ".join([purpose, *lines])):
        if d not in src_digits:
            problems.append(f"재료에 없는 숫자 {d}")
    joined = " ".join([purpose, *lines])
    for term in FORBIDDEN_TERMS:
        if term in joined:
            problems.append(f"금지 표현 {term}")
    return problems
