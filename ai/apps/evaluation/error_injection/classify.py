# Requirement: E-3
"""(정답, STT 출력) → 편집 유형. **프로파일을 손으로 적지 않기 위한 코드다.**

어느 편집을 어느 유형으로 셀지가 사람 판단이면 프로파일이 재현되지 않는다. 규칙을 여기 고정하고
`scripts/build_stt_error_profile.py` 가 실측 쌍 전체에 돌린다. 규칙을 바꾸면 프로파일을 다시 뽑는다.

유형 — 위에서부터 먼저 맞는 것 하나로 센다:

| 유형 | 판정 규칙 (공백을 뺀 두 구간 `a`·`b` 기준) | 주입기가 흉내 내는가 |
|---|---|---|
| `spacing_merge` / `spacing_split` | `a == b`, 단어 수가 줄었다 / 늘었다 | ✅ |
| `word_delete` · `word_insert` | 한쪽이 비었다 | 삭제 ✅ · 삽입 ❌(넣을 말을 지어내야 한다) |
| `number_verbalize` | 숫자가 한쪽에만 있고, 숫자·수사를 뺀 나머지가 비슷하다(유사도 ≥ 0.6) | ✅ (자릿수 읽기) |
| `jamo_sub` | 음절 수가 같고, 달라진 음절마다 **자모 한 자리만** 다르다 | ✅ (실측 혼동표 안에서만) |
| `ending_drop` · `ending_add` | 한쪽이 다른 쪽의 앞부분이다 | 탈락 ✅ · 추가 ❌ |
| `unmodeled` | 나머지 — 환청·의미 붕괴·여러 자모가 바뀐 치환 | ❌ |

⚠ **`unmodeled` 비율이 곧 이 주입기의 한계다.** 주입기는 그 몫을 흉내 내지 않으므로, 같은 WER 이라도
실제 STT 오류보다 **덜 파괴적인** 오류를 넣는다 — 곡선은 낙관 쪽으로 기운다. 곡선 옆에 이 비율을 함께 적는다.
"""

from __future__ import annotations

import difflib
import re
from collections import Counter
from dataclasses import dataclass, field

from .hangul import is_syllable, jamo_diff

TYPES = (
    "spacing_merge", "spacing_split", "word_delete", "word_insert", "number_verbalize",
    "jamo_sub", "ending_drop", "ending_add", "unmodeled",
)

_DIGIT = re.compile(r"\d")
_NUMERAL = re.compile(r"[공영일이삼사오육칠팔구십백천만한두세네]")


def _is_number_verbalize(digits_side: str, words_side: str) -> bool:
    """숫자가 한쪽에만 있고, **숫자와 한글 수사를 뺀 나머지가 거의 같다.**

    나머지 조건이 없던 첫 판은 「숫자로 시작한 뒤 문장 전체가 무너진 환청」까지 여기로 셌다
    (2026-09-14 실측 쌍에서 6건 중 절반) — 흉내 낼 수 있는 유형으로 세면 주입기의 한계가 작게 보인다.
    """
    if not _DIGIT.search(digits_side) or _DIGIT.search(words_side) or not _NUMERAL.search(words_side):
        return False
    rest_a, rest_b = _DIGIT.sub("", digits_side), _NUMERAL.sub("", words_side)
    return difflib.SequenceMatcher(a=rest_a, b=rest_b, autojunk=False).ratio() >= 0.6


@dataclass
class EditProfile:
    counts: Counter = field(default_factory=Counter)
    # (자리, 정답 자모, STT 자모) → 건수. 주입기가 이 표 **밖의** 혼동을 만들지 않는다
    jamo_confusions: Counter = field(default_factory=Counter)
    reference_words: int = 0
    pairs: int = 0


def classify_span(a_words: list[str], b_words: list[str]) -> tuple[str, list[tuple[str, str, str]]]:
    """한 편집 구간의 유형과(자모 치환이면) 혼동 목록."""
    a, b = "".join(a_words), "".join(b_words)
    if a == b:
        return ("spacing_merge" if len(b_words) < len(a_words) else "spacing_split"), []
    if not b_words:
        return "word_delete", []
    if not a_words:
        return "word_insert", []
    if _is_number_verbalize(a, b) or _is_number_verbalize(b, a):
        return "number_verbalize", []
    if len(a) == len(b) and all(is_syllable(x) and is_syllable(y) for x, y in zip(a, b) if x != y):
        diffs = [jamo_diff(x, y) for x, y in zip(a, b) if x != y]
        if diffs and all(len(d) == 1 for d in diffs):
            return "jamo_sub", [d[0] for d in diffs]
    if len(b) < len(a) and a.startswith(b):
        return "ending_drop", []
    if len(a) < len(b) and b.startswith(a):
        return "ending_add", []
    return "unmodeled", []


def accumulate(profile: EditProfile, reference: str, hypothesis: str) -> None:
    """정규화된 (정답, 가설) 한 쌍을 프로파일에 더한다. 정규화는 부르는 쪽 몫이다(`metrics/asr.py`)."""
    rw, hw = reference.split(), hypothesis.split()
    profile.pairs += 1
    profile.reference_words += len(rw)
    matcher = difflib.SequenceMatcher(a=rw, b=hw, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        kind, confusions = classify_span(rw[i1:i2], hw[j1:j2])
        profile.counts[kind] += 1
        profile.jamo_confusions.update(confusions)
