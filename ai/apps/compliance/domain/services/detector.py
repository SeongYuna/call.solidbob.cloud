# Requirement: C-1, C-2, C-3, C-4
"""상담원 발화 → 위반 목록. 규칙표는 `value_objects/rules.py`.

**재현율 우선이다**(검수 기준 재현율 ≥0.90 · 정밀도 ≥0.60). 애매하면 잡는다 — 다만 **요청을 말리는 말**
(「주민번호는 말씀하지 않으셔도 됩니다」)은 C-2 에서 뺀다. 그건 매뉴얼이 권하는 응대라 잡으면 경고가 거꾸로 선다.

발견이 없으면 빈 목록이다 — **「잡힌 것이 없음」이지 「안전함」이 아니다**(부록 A-1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..value_objects.rules import (
    C1_EXEMPT,
    HEALTH_CONTEXT,
    PROXY_ACTION,
    PROXY_REQUIRED_MENTION,
    REQUEST,
    REQUEST_NEGATED,
    RULES,
)

_COMPILED = tuple((r, re.compile(r.pattern)) for r in RULES)
_REQUEST = re.compile(REQUEST)
_REQUEST_NEGATED = re.compile(REQUEST_NEGATED)
_PROXY_ACTION = re.compile(PROXY_ACTION)
_PROXY_MENTION = re.compile(PROXY_REQUIRED_MENTION)
_C1_EXEMPT = re.compile(C1_EXEMPT)
_HEALTH = re.compile(HEALTH_CONTEXT)


@dataclass(frozen=True)
class Detection:
    code: str
    phrase: str
    start: int
    end: int
    alternative_doc_id: str


def detect(agent_utterance: str) -> list[Detection]:
    text = agent_utterance or ""
    if not text.strip():
        return []

    asks = bool(_REQUEST.search(text)) and not _REQUEST_NEGATED.search(text)
    health = bool(_HEALTH.search(text))
    exempt_c1 = [(m.start(), m.end()) for m in _C1_EXEMPT.finditer(text)]
    found: list[Detection] = []
    for rule, rx in _COMPILED:
        if (rule.needs_request and not asks) or (rule.needs_health and not health):
            continue
        for m in rx.finditer(text):
            if rule.code == "C-1" and any(s <= m.start() < e for s, e in exempt_c1):
                continue
            found.append(Detection(rule.code, m.group(0), m.start(), m.end(), rule.alternative_doc_id))

    # 대리 신청을 처리해 주겠다면서 위임장·신분증을 말하지 않았다 (MANUAL-3.1)
    m = _PROXY_ACTION.search(text)
    if m and not _PROXY_MENTION.search(text):
        found.append(Detection("C-3", m.group(0), m.start(), m.end(), "DASAN-MANUAL-3.1"))

    return _dedupe(found)


def _dedupe(found: list[Detection]) -> list[Detection]:
    """같은 코드로 겹친 구간은 넓은 쪽 하나만 남긴다. 코드가 다르면 둘 다 남긴다(갈래마다 대응이 다르다)."""
    out: list[Detection] = []
    for d in sorted(found, key=lambda x: (x.start, -(x.end - x.start))):
        if any(o.code == d.code and o.start < d.end and d.start < o.end for o in out):
            continue
        out.append(d)
    return out
