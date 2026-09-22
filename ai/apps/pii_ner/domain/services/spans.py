# Requirement: C-5
"""NER 토큰 태그 → P6(인명)·P7(상세주소) 구간.

**판정은 규칙이다**(절대 원칙 9). 모델은 «이 토큰이 사람 이름·지명처럼 보인다» 까지만 말하고,
어디부터 어디까지를 가릴지는 아래 규칙이 정한다. 같은 태그가 들어오면 같은 구간이 나온다.

**지표 우선순위를 코드에 고정한다** — `server/apps/masking` 과 같다:

    누락 0건  >  과잉 마스킹 억제.  애매하면 가린다.

그래서 경계가 애매하면 **넓게** 잡는다. 서브워드 태깅이라 모델은 이름 끝 글자를 자주
놓친다(2026-09-15 실측: `"오세준이고"` 에서 `"오세"` 만 PER). 이름의 뒷글자가 노출되면
그건 누락이다 — 그래서 **어절 끝까지 넓힌 다음 조사만 벗긴다.** 모르는 어미가 붙어
벗기지 못하면 어절째 가린다.
"""

from __future__ import annotations

import re
from typing import Callable, Iterable

from ..value_objects.entity import EntitySpan, TokenTag

_HANGUL = re.compile(r"[가-힣]")

# 이름·주소 뒤에 붙는 조사·서술어. **긴 것부터** 대조한다 — `"이고요"` 가 `"요"` 로 벗겨지면
# `"이고"` 가 이름 쪽에 남는다. 확장한 꼬리(모델이 PER 로 준 구간 **밖**)에서만 벗기므로
# 모델이 이름이라고 한 글자를 먹지는 않는다.
PARTICLES: tuple[str, ...] = tuple(
    sorted(
        {
            "이었는데요", "이었는데", "이라고요", "이라고", "이라는", "이에요", "이예요",
            "입니다", "이고요", "인데요", "이지만", "에서요", "으로요", "이세요",
            "한테", "에게", "께서", "이고", "이며", "인데", "이란", "이랑", "에서",
            "으로", "예요", "이요", "씨가", "씨는", "씨", "님이", "님은", "님",
            "은", "는", "이", "가", "을", "를", "과", "와", "도", "의", "로", "에", "요",
        },
        key=len,
        reverse=True,
    )
)

# 꼬리에서 조사를 벗긴 뒤에도 이만큼보다 길게 남으면 «이름의 나머지» 가 아니라
# 모르는 활용이다. 그때는 어절째 가린다(애매하면 가린다).
_MAX_NAME_TAIL = 2

# P7 번지·동·호 어절. **앞부분만** 주소로 본다 — `"12에서"` 는 `"12"`, `"1104호예요"` 는 `"1104호"`.
_ADDRESS_NUMBER = re.compile(
    r"\d+(?:-\d+)?(?:번지|번길|길|호|동|층|번|가)?(?:\s?\d+(?:-\d+)?(?:호|동|층))?"
)
# 도로명: `"정릉로"`·`"월드컵북로"`·`"테헤란로"`·`"77길"` 은 번호 규칙이 잡는다
_ROAD_SUFFIX = re.compile(r"[가-힣]+(?:로|길|대로)\d*$")

# 지명·도로명으로 인정하는 개체 유형. `monologg/koelectra-base-v3-naver-ner` 기준 —
# 도로명(`테헤란로`)을 LOC 가 아니라 AFW(인공물)로 준다(2026-09-15 실측).
_PLACE_LABELS = frozenset({"LOC", "AFW"})


def _strip_tail(tail: str) -> str:
    for p in PARTICLES:
        if tail.endswith(p):
            return tail[: -len(p)]
    return tail


def _eojeol_bounds(text: str) -> list[tuple[int, int]]:
    """공백으로 가른 어절의 `[start, end)` 목록."""
    return [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]


def _overlaps(tag: TokenTag, start: int, end: int) -> bool:
    return tag.start < end and start < tag.end


def person_spans(text: str, tags: Iterable[TokenTag]) -> list[EntitySpan]:
    """P6. PER 토큰을 붙여 이름 덩어리를 만들고, 어절 끝까지 넓힌 뒤 조사를 벗긴다.

    한글이 한 글자도 없는 PER 는 버린다 — 카드번호 가운데 `"89"` 를 PER 로 준 실측이 있다
    (그 숫자는 P2 규칙이 이미 가린다).
    """
    per = sorted((t for t in tags if t.label == "PER"), key=lambda t: t.start)
    merged: list[list[int]] = []
    for t in per:
        if merged and t.start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], t.end)
        else:
            merged.append([t.start, t.end])

    found: list[EntitySpan] = []
    for start, end in merged:
        if not _HANGUL.search(text[start:end]):
            continue
        # 어절 끝 = 한글 음절이 끊기는 곳. 숫자·문장부호·공백에서 멈춘다.
        eojeol_end = end
        while eojeol_end < len(text) and _HANGUL.match(text[eojeol_end]):
            eojeol_end += 1
        tail = _strip_tail(text[end:eojeol_end])
        name_end = end + len(tail) if len(tail) <= _MAX_NAME_TAIL else eojeol_end
        found.append(EntitySpan("P6", start, name_end))
    return found


def _number_prefix_end(text: str, start: int, end: int) -> int | None:
    """어절이 번지·동·호로 **시작하고** 나머지가 조사뿐이면 번호 부분의 끝. 아니면 None.

    `"25만원을"` 은 `"25"` 뒤가 `"만원을"` 이라 주소 번호가 아니다.
    """
    word = text[start:end]
    m = _ADDRESS_NUMBER.match(word)
    if not m:
        return None
    rest = word[m.end():]
    if rest and _strip_tail(rest) != "":
        return None
    return start + m.end()


def address_spans(text: str, tags: Iterable[TokenTag]) -> list[EntitySpan]:
    """P7. **지명·도로명 어절과 번호 어절이 이어진 덩어리**만 상세주소로 본다.

    - 지명·도로명: NER 이 LOC·AFW 를 준 어절. 도로명은 `…로`·`…길` 로 끝나야 한다
      (AFW 는 도로가 아닌 인공물에도 붙는다)
    - 번호: `123번지`·`2동`·`1104호`·`77길`·`12` — 뒤에 조사만 붙을 수 있다

    **둘 다 있어야 한다.** `"서울시 강남구"` 만으로는 상세주소가 아니고(자막에서 구 이름을
    지우면 민원 위치가 사라진다), `"1234 번지 앞에"` 는 지명이 없다.
    """
    tags = list(tags)
    words = _eojeol_bounds(text)

    kinds: list[str | None] = []  # "place" | "number" | None
    ends: list[int] = []
    for s, e in words:
        num_end = _number_prefix_end(text, s, e)
        if num_end is not None:
            kinds.append("number")
            ends.append(num_end)
            continue
        place_tags = [t for t in tags if t.label in _PLACE_LABELS and _overlaps(t, s, e)]
        if any(t.label == "LOC" for t in place_tags):
            kinds.append("place")
            ends.append(e)
        elif place_tags and (
            _ROAD_SUFFIX.search(text[s:e]) or _ROAD_SUFFIX.search(_strip_tail(text[s:e]))
        ):
            kinds.append("place")
            ends.append(e)
        else:
            kinds.append(None)
            ends.append(e)

    found: list[EntitySpan] = []
    i = 0
    while i < len(words):
        if kinds[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < len(words) and kinds[j + 1] is not None:
            j += 1
        run = kinds[i : j + 1]
        if "place" in run and "number" in run:
            found.append(EntitySpan("P7", words[i][0], ends[j]))
        i = j + 1
    return found


def merge_spans(spans: Iterable[EntitySpan]) -> list[EntitySpan]:
    """겹치는 구간을 합친다. 합친 구간의 패턴은 **더 넓었던 쪽**을 따른다."""
    out: list[EntitySpan] = []
    for s in sorted(spans, key=lambda x: (x.start, -(x.end - x.start))):
        if out and s.start < out[-1].end:
            prev = out[-1]
            wider = prev if (prev.end - prev.start) >= (s.end - s.start) else s
            out[-1] = EntitySpan(wider.pattern, prev.start, max(prev.end, s.end))
        else:
            out.append(s)
    return out


def detect_entities(text: str, tags: Iterable[TokenTag]) -> list[EntitySpan]:
    tags = list(tags)
    return merge_spans([*person_spans(text, tags), *address_spans(text, tags)])


# 붙이지 않는 한 글자 어절 — 감탄사·대명사·부사·수 관형사. 쪼개진 이름의 첫 글자(성씨)가 아니다.
# 2026-09-17 AI Hub 실제 발화에서 「네 이제」→「네이제」·「네 제 이름은」→「네제이름은」 을 모델이 인명으로 태깅했다.
# 「이·한·전」 은 흔한 성씨라 넣지 않는다(`"이 민준"` 을 놓치는 쪽이 더 나쁘다 — 「이 지원」 같은 과잉은 남는다).
_FUNCTION_SYLLABLES = frozenset("네예아어음응그저제또좀잘더꼭안못다두세뭐왜즉단및등위앞뒤옆속곳때것수중후내외첫새온총각")


def join_split_syllables(text: str) -> tuple[str, list[int]]:
    """**1음절 한글 어절**을 이웃 어절에 붙인 사본과, 사본 글자 → 원문 글자 오프셋 표.

    STT 띄어쓰기 오류(`spacing_split`, 실측 프로파일 2위)가 이름·도로명을 쪼개면 모델도 경계 규칙도 못 잡는다
    (2026-09-15 오류 내성 곡선: `"김 민준"` · `"성북구 정 릉로"` — 규칙+NER 누락 2건이 전부 이것). 붙인 사본을 한 번 더
    태깅해 합집합을 가린다.

    붙이는 쪽: **오른쪽 이웃이 2음절 이상이면 오른쪽**(`김 민준` → `김민준`, `정 릉로` → `정릉로`), 아니면 **왼쪽 이웃이
    2음절 이상일 때 왼쪽**(`김민 준` → `김민준`). 1음절끼리는 붙이지 않는다 — `"그 김 민준"` 에서 `"그"` 까지 붙으면
    모델 입력이 원문에서 멀어진다. 정상 띄어쓰기(`"서울시 강남구"`)는 건드리지 않는다.
    """
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]

    def one_syllable(i: int) -> bool:
        a, b = words[i]
        return b - a == 1 and bool(_HANGUL.match(text[a])) and text[a] not in _FUNCTION_SYLLABLES

    def hangul_word(i: int) -> bool:
        a, b = words[i]
        return b - a >= 2 and bool(_HANGUL.search(text[a:b]))

    drop: set[int] = set()  # 지울 공백의 원문 위치
    for i in range(len(words)):
        if not one_syllable(i):
            continue
        if i + 1 < len(words) and hangul_word(i + 1) and text[words[i][1] : words[i + 1][0]] == " ":
            drop.add(words[i][1])
        elif i > 0 and hangul_word(i - 1) and text[words[i - 1][1] : words[i][0]] == " ":
            drop.add(words[i - 1][1])
    keep = [i for i in range(len(text)) if i not in drop]
    return "".join(text[i] for i in keep), keep


def map_spans_back(spans: Iterable[EntitySpan], index_map: list[int]) -> list[EntitySpan]:
    """사본 오프셋 구간을 원문 오프셋으로. 끝은 마지막 글자의 원문 위치 + 1 — 사이에 지운 공백까지 덮는다."""
    return [EntitySpan(s.pattern, index_map[s.start], index_map[s.end - 1] + 1) for s in spans]


def detect_entities_with_rejoin(text: str, tag: Callable[[str], list[TokenTag]]) -> list[EntitySpan]:
    """P6·P7 구간 — 원문 한 번 + 1음절을 붙인 사본 한 번(`join_split_syllables`)의 합집합.

    `LayeredMaskingAdapter`(같은 프로세스)와 모델 HTTP 표면(`model_serving`, `decisions/213`)이 **같은 함수**를 쓴다 —
    원격으로 옮겼다고 구간 규칙이 달라지면 운영과 측정이 다른 것을 재게 된다. `tag` 가 올린 예외는 그대로 위로 간다
    (규칙 폴백 여부는 부르는 쪽이 정한다).
    """
    entities = detect_entities(text, tag(text))
    joined, index_map = join_split_syllables(text)
    if joined != text:
        entities += map_spans_back(detect_entities(joined, tag(joined)), index_map)
    return merge_spans(entities)
