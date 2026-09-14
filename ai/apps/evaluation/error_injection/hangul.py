# Requirement: E-3
"""한글 음절 ↔ 자모. 유니코드 합성 공식(U+AC00 + (초성×21 + 중성)×28 + 종성)만 쓴다."""

from __future__ import annotations

CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = ("", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ",
        "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ")

_BASE, _LAST = 0xAC00, 0xD7A3
SLOTS = ("cho", "jung", "jong")


def is_syllable(ch: str) -> bool:
    return len(ch) == 1 and _BASE <= ord(ch) <= _LAST


def decompose(ch: str) -> tuple[str, str, str]:
    """완성형 음절 → (초성, 중성, 종성). 종성이 없으면 빈 문자열."""
    if not is_syllable(ch):
        raise ValueError(f"완성형 한글 음절이 아니다: {ch!r}")
    code = ord(ch) - _BASE
    return CHO[code // 588], JUNG[(code % 588) // 28], JONG[code % 28]


def compose(cho: str, jung: str, jong: str = "") -> str:
    return chr(_BASE + (CHO.index(cho) * 21 + JUNG.index(jung)) * 28 + JONG.index(jong))


def jamo_diff(a: str, b: str) -> list[tuple[str, str, str]]:
    """두 음절에서 달라진 자리 목록 — `[(자리, a 의 자모, b 의 자모)]`."""
    return [(slot, x, y) for slot, x, y in zip(SLOTS, decompose(a), decompose(b)) if x != y]
