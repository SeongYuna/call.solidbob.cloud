# Requirement: C-5, SEC-1
"""중간 자막(interim) 전용 가드 — 번호가 **다 들어오기 전**의 숫자 덩어리를 가린다.

확정 규칙(`pii_detector`)은 완성된 번호만 잡는다 — 휴대전화 10~11자리, 카드 14~16자리, 계좌 10~14자리.
중간 자막은 번호가 들어오는 중이라 `9410 0000`(8자리)·`010 0000`(7자리)이 어느 패턴에도 맞지 않고,
**운영 표본 6건 중 5건이 화면에 그대로 나갔다**(미결 「C-5 중간 자막」, 2026-09-22). 확정 자막·DB 는 가려졌다.

중간 자막은 곧 확정 자막으로 덮이므로 **넓게 가린다** — 절대 원칙 3 「애매하면 가린다」:

- 구분자·공백을 걷은 뒤 **3자리 이상 이어진 숫자**(낭독형 「공일공」 포함)는 전부 가린다
- 두 자리 이하(「2개」·「30분」)는 남긴다 — 자막이 읽혀야 한다(P5 가 문맥 없는 4자리를 안 가리는 것과 같은 이유)
- 구분자는 남긴다 — `010-12` → `***-**`. 자릿수를 보존해 오프셋이 어긋나지 않게 한다

**확정 자막에는 쓰지 않는다.** 확정 규칙은 골든셋으로 채점되고, 여기처럼 넓히면 금액·호수까지 지워진다.
⚠ 알려진 과잉: 띄어 쓴 한자어 숫자가 이어지면(「이 일이」 → 이일이) 중간 자막에서만 가려진다 — 확정에서 돌아온다.
"""

from __future__ import annotations

import re

from ..value_objects.pii_pattern import MASK_CHAR, PiiSpan
from .number_normalizer import sino_to_digits, strip_separators
from .pii_detector import _PATTERN_CONTEXT

MIN_INTERIM_DIGITS = 3
_RUN = re.compile(rf"\d{{{MIN_INTERIM_DIGITS},}}")


def _label(text: str, digits: str) -> str:
    """P1~P7 안에서 고른다 — 새 패턴을 만들지 않는다(`pii_pattern.py`, 프론트 계약도 P1~P7 뿐).

    문맥어가 있으면 그 패턴, 없으면 0 으로 시작하면 전화(P4), 그 밖은 가장 넓은 숫자 패턴인 계좌(P3).
    중간 자막 라벨은 곧 확정 라벨로 바뀐다.
    """
    for pattern, words in _PATTERN_CONTEXT.items():
        if any(w in text for w in words):
            return pattern
    return "P4" if digits.startswith("0") else "P3"


def guard_interim(text: str) -> tuple[str, tuple[PiiSpan, ...]]:
    """(가린 텍스트, 구간)을 돌려준다. 가릴 것이 없으면 원문 그대로와 빈 튜플. 이미 `*` 인 글자는 숫자가 아니라 건너뛴다."""
    normalized, index_map = strip_separators(text)
    digits, _ = sino_to_digits(normalized)
    runs = list(_RUN.finditer(digits))
    if not runs:
        return text, ()

    chars = list(text)
    spans: list[PiiSpan] = []
    for m in runs:
        for i in range(m.start(), m.end()):
            chars[index_map[i]] = MASK_CHAR  # 숫자 자리만 — 사이의 구분자는 남긴다
        spans.append(PiiSpan(pattern=_label(text, m.group()), start=index_map[m.start()], end=index_map[m.end() - 1] + 1))
    return "".join(chars), tuple(spans)
