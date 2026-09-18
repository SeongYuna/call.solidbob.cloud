# Requirement: C-5
"""탐지 파이프라인 ③ — 패턴 매칭. P1~P5 는 숫자 정규식, P6·P7 은 문맥·토큰 규칙이다.

P6(인명)·P7(상세주소)은 [2.4절](/docs/02/)이 NER 로 정했지만 모델은 `ai/` 몫이라
(계약 2 가 `server/` 의 `transformers` import 를 막는다) **규칙으로 바닥을 깔았다.**
각 모듈의 docstring 이 무엇을 못 잡는지 적어 두었다 — NER 이 붙으면 폴백으로 남는다.

**지표 우선순위를 코드에 고정한다** ([2.4절](/docs/02/)):

    누락 0건  >  과잉 마스킹 억제.  애매하면 가린다.

그래서 겹치는 구간이 생기면 **더 넓은 쪽**을 남긴다. 자릿수 범위가 겹치는 패턴
(카드 14~16 / 계좌 10~14)에서 좁은 쪽을 고르면 뒷자리가 노출된다.

**정규화된 문자열 위에서 찾고, 원문 오프셋으로 되돌린다.** 구분자가 있든 없든
같은 번호를 잡기 위해서다 — `"123456 1234567"` 과 `"1234561234567"` 둘 다 포착한다.
"""

from __future__ import annotations

import re

from ..value_objects.pii_pattern import PiiSpan
from .address_detector import detect_addresses
from .name_detector import detect_names
from .number_normalizer import sino_to_digits, strip_separators

# P5 인증번호는 문맥이 있을 때만 잡는다 — 4~6자리 숫자는 금액·개수와 구분이 안 된다.
# 애매하면 가린다는 원칙과 충돌하지 않는다: 문맥 없는 4자리를 전부 가리면
# "3천원"·"2개" 까지 지워져 자막이 읽히지 않는다(자막 자체가 못 쓰게 되는 것이 더 큰 손실).
AUTH_CONTEXT = ("인증", "승인", "확인번호", "코드", "otp", "OTP", "비밀번호", "핀번호")

# 정규화된(구분자 없는) 숫자열 기준. 긴 것부터 본다 — 겹치면 넓은 쪽이 이긴다.
_NUMERIC_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("P1", re.compile(r"\d{13}")),           # 주민등록번호 13자리
    ("P2", re.compile(r"\d{14,16}")),        # 카드번호 14~16자리
    ("P4", re.compile(r"01\d{8,9}")),        # 휴대전화 010/011… 10~11자리
    ("P4", re.compile(r"0(?:2|[3-6][1-5])\d{7,8}")),  # 집·사무실 전화(지역번호) 9~11자리 — GS-409 가 P3(계좌)로 불렸다
    ("P3", re.compile(r"\d{10,14}")),        # 계좌번호 10~14자리
]


def _to_source_span(pattern: str, start: int, end: int, index_map: list[int]) -> PiiSpan:
    """정규화 문자열의 [start, end) 를 원문 오프셋으로 되돌린다."""
    return PiiSpan(pattern=pattern, start=index_map[start], end=index_map[end - 1] + 1)


# 낭독형 휴대전화 뒤에 붙은 「이에요」·「이요」 의 「이」 가 2 로 바뀌어 11자리가 12자리 계좌(P3)로 읽힌다
# (합성 대본 SYN-011~021 「공일공 공공공공 공일일육이에요」, 2026-09-18). 라벨만 P4 로 바로잡고 **구간은 넓은 쪽을 둔다** —
# 「이」 가 진짜 끝자리 2 일 수도 있어서다(누락 0건 > 과잉 억제).
_MOBILE = re.compile(r"01[016789]\d{7,8}")
_COPULA_AFTER_I = ("에요", "예요", "요", "고", "구", "라", "며", "면", "야", "죠", "지", "니")


def _read_mobile_with_copula(name: str, m: re.Match[str], normalized: str, digits: str) -> str:
    if name != "P3":
        return name
    run = digits[m.start():m.end()]
    mobile = _MOBILE.match(run)
    if mobile is None or mobile.end() != len(run) - 1:
        return name
    if normalized[m.end() - 1] == "이" and normalized[m.end():].startswith(_COPULA_AFTER_I):
        return "P4"
    return name


def _detect_numeric(text: str) -> list[PiiSpan]:
    normalized, index_map = strip_separators(text)
    digits, _ = sino_to_digits(normalized)  # ② 보조 — 낭독형 숫자를 잡기 위해서만 쓴다

    found: list[PiiSpan] = []
    for name, rule in _NUMERIC_RULES:
        for m in rule.finditer(digits):
            label = _read_mobile_with_copula(name, m, normalized, digits)
            found.append(_to_source_span(label, m.start(), m.end(), index_map))
    return found


def _detect_auth_code(text: str) -> list[PiiSpan]:
    """P5 — 문맥 단어가 같은 발화에 있을 때만 4~6자리를 잡는다."""
    lowered = text.lower()
    if not any(k.lower() in lowered for k in AUTH_CONTEXT):
        return []

    normalized, index_map = strip_separators(text)
    digits, _ = sino_to_digits(normalized)
    return [
        _to_source_span("P5", m.start(), m.end(), index_map)
        for m in re.finditer(r"(?<!\d)\d{4,6}(?!\d)", digits)
    ]


# 자릿수만으로는 갈리지 않는 패턴이 있다 — **13자리는 주민등록번호(P1)이면서 계좌번호
# (P3, 10~14)이기도 하다.** 글자는 어느 쪽으로 잡아도 가려지지만 **라벨이 틀리면 화면과
# 리포트가 "주민등록번호"라고 거짓말한다.** 그래서 같은 구간에 여러 패턴이 걸리면
# 발화의 문맥어로 가른다 — P5(인증번호)가 이미 쓰는 방식과 같다.
_PATTERN_CONTEXT: dict[str, tuple[str, ...]] = {
    "P1": ("주민등록번호", "주민번호", "주민"),
    "P2": ("카드번호", "신용카드", "체크카드", "카드"),
    "P3": ("계좌번호", "계좌", "이체", "입금", "송금"),
    "P4": ("휴대전화", "휴대폰", "핸드폰", "전화번호", "연락처", "전화"),
}


def _disambiguate(text: str, spans: list[PiiSpan]) -> list[PiiSpan]:
    """구간이 **정확히 같은** 후보들 중 하나만 남긴다. 문맥어가 있으면 그쪽, 없으면 규칙 순서.

    구간이 다른 겹침(카드 14~16 vs 계좌 10~14)은 여기서 건드리지 않는다 — 그건 아래
    `_resolve_overlaps` 가 「넓은 쪽」으로 처리한다. 여기는 **같은 글자를 두 이름으로 부르는**
    경우만 다룬다.
    """
    groups: dict[tuple[int, int], list[PiiSpan]] = {}
    for span in spans:
        groups.setdefault((span.start, span.end), []).append(span)

    picked: list[PiiSpan] = []
    for candidates in groups.values():
        if len(candidates) == 1:
            picked.append(candidates[0])
            continue
        # 규칙 선언 순서대로 보되, 문맥어가 있는 첫 후보를 고른다.
        by_context = next(
            (c for c in candidates
             if any(k in text for k in _PATTERN_CONTEXT.get(c.pattern, ()))),
            None,
        )
        picked.append(by_context or candidates[0])
    return picked


def _resolve_overlaps(spans: list[PiiSpan]) -> list[PiiSpan]:
    """겹치면 **넓은 쪽**을 남긴다 — 좁은 쪽을 고르면 뒷자리가 노출된다(누락 0건 우선)."""
    ordered = sorted(spans, key=lambda s: (-s.length, s.start))
    kept: list[PiiSpan] = []
    for span in ordered:
        if not any(span.overlaps(k) for k in kept):
            kept.append(span)
    return sorted(kept, key=lambda s: s.start)


def detect(text: str) -> list[PiiSpan]:
    """P1~P7 을 찾는다. 결과는 원문 오프셋 기준이고 시작 위치 순으로 정렬된다."""
    found = (
        _detect_numeric(text)
        + _detect_auth_code(text)
        + detect_names(text)
        + detect_addresses(text)
    )
    return _resolve_overlaps(_disambiguate(text, found))
