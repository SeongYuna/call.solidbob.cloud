# Requirement: C-5
"""탐지 파이프라인 ③ 확장 — P6 인명.

⚠ **이것은 NER 이 아니다.** [2.4절](/docs/02/)은 P6 를 NER 로 정했고 그 판단은 유효하다 —
모델 없이 임의의 한국어 이름을 찾을 수는 없다. 다만 `server/.importlinter` 계약 2 가
`server/` 안에서 `transformers` import 를 금지하므로 **모델은 `ai/` 몫**이다(`ai/apps/pii_ner`, 운영 반영은 `decisions/208`).

그때까지 **이름이 흐르는 말버릇이 있을 때만** 잡는다. 네 갈래다.

1. **문맥** — `"제 이름은 김민준이고"`·`"성함이 홍길동입니다"`. 띄어 쓴 외국인 이름(`"이름 제니 레예스"`)은 세 어절까지 본다
2. **자기소개** — `"저는 최지훈이고요"`·`"저는 강민재고요"`. 「저는」 은 흔한 말이라 **이름을 밝히는 어미**가 붙을 때만.
   가족 호칭(`"아버지는 강영식이에요"`)도 같은 자리로 본다(2026-09-18)
3. **호칭** — `"그 김민준 씨가"`·`"김도윤 고객님"`·`"제니 레예스 고객님"`. 상담원이 고객을 부르는 자리다
4. **이름만 답한 발화** — `"박성호요."`·`"한지영이요."`. 앞 턴의 「성함이?」 에 답한 모양이라 발화(문장) 첫머리만 본다

2~4 는 **성씨로 시작할 때만**(외국인 이름 두 어절 호칭은 예외) 받고, 성씨로 시작하는 일상어(`"정확히요"`·`"우리 고객님"`)는
`_NOT_NAMES` 로 뺀다. 2026-09-17 AI Hub 실제 발화 20,278건에서 잘못 가린 조각(「명의 변경」·「성함은 어떻게」)을 보고 넣었다.

**문맥·호칭이 전혀 없는 이름(`"김민준 그 사람이"`)은 못 잡는다** — 그 사실을 테스트로 고정해 둔다.
문맥 없이 2~4자 한글을 전부 가리면 **자막 자체가 못 쓰게 된다**(P5 인증번호가 문맥을 요구하는 것과 같은 이유).
"""

from __future__ import annotations

import re

from ..value_objects.pii_pattern import PiiSpan
from .address_detector import WIDE_AREA_NAMES

# ── 1. 문맥 ─────────────────────────────────────────────────────────────────
# **목적격(을·를)은 뺀다.** `"이름을 바꾸고"` 는 이름이 무엇인지 밝히는 말이 아니다.
# `명의(?!자)` — `"명의자분"` 에서 「명의」 까지만 문맥으로 잡고 「자분」 을 이름으로 보던 것(실제 7건)을 막는다.
# 문맥 뒤는 **조사(은·는·이·가) 또는 띄어쓰기**여야 한다 — `"성함과"`·`"명의의"`·`"이름으로"` 는 이름을 밝히는 말이 아니다(실제 발화).
# 「명의」 는 조사가 있을 때만 — `"사업자 명의 통장사본"` 처럼 뒤에 보통 명사가 흔하다. 앞은 단어 경계 — `"2명의 승객"` 안의 「명의」 를 막는다.
_CONTEXT = re.compile(
    r"(?<![가-힣0-9])(?:(?:이름|성함|본인\s*이름)(?:\s*(?:은|는|이|가)\s*|\s+)|(?:명의자|명의)(?:은|는|이|가)\s*)(?=[가-힣])(?![을를분])"
)
# 자기소개 — 뒤 어절이 이름을 밝히는 어미로 끝나야 한다(`"저는 괜찮아요"` 는 이름이 아니다)
_SELF_INTRO = re.compile(r"(?:^|(?<=[\s,.]))(?:저는|전)\s+(?=[가-힣])")
# 가족 호칭 — `"아버지는 강영식이에요"`(SYN-020, 2026-09-18 E2E 에서 원문으로 남았다). 「저는」 과 같은 자리다
_FAMILY_INTRO = re.compile(
    r"(?:^|(?<=[\s,.]))(?:아버지|어머니|아버님|어머님|아빠|엄마|남편|아내|집사람|배우자|아들|딸|형|누나|오빠|언니|동생|"
    r"할머니|할아버지|자녀|손자|손녀|며느리|사위|장인|장모|시어머니|시아버지)(?:분|님)?(?:은|는|이|가)\s+(?=[가-힣])"
)
# 이름을 밝히는 어미. **긴 것부터** 본다 — `"강민재고요"` 는 「이고요」 가 아니라 「고요」 다(모음으로 끝나는 이름).
_INTRO_ENDINGS = tuple(sorted((
    "이고요", "이구요", "이고", "입니다", "이에요", "이예요", "예요", "에요", "이라고", "라고", "인데요", "이며", "고요", "구요", "이야", "야",
), key=len, reverse=True))

# 이름 뒤에 붙는 조사·서술어. **긴 것부터** 벗겨야 `"이고요"` 가 `"이고"` 로, `"이고"` 가 `"이"` 로 잘리지 않는다.
# 홑글자 `"고"` 는 넣지 않는다 — `"바꾸고"` 가 `"바꾸"` 로 남아 이름이 되어버린다.
_PARTICLES = tuple(sorted((
    "이라고요", "이라고", "이라는", "이고요", "이구요", "이에요", "인데요", "입니다", "이지만",
    "예요", "이고", "이며", "인데", "이란", "으로", "이요", "님", "씨", "은", "는", "이", "가", "을", "를", "요",
), key=len, reverse=True))

# ── 3·4. 성씨 ───────────────────────────────────────────────────────────────
_SURNAMES_1 = set(
    "김이박최정강조윤장임한오서신권황안송류유전홍고문양손배백허남심노하곽성차주우구민진지엄채원천방공현함변염여추도소석선설마길연위표명기반왕금옥육인맹제모탁국어은편용예경봉사부"
)
_SURNAMES_2 = ("남궁", "황보", "제갈", "선우", "독고", "사공", "서문")

_AFTER_HONORIFIC = r"(?:께서|에게|께|이|가|은|는|을|를|의|도)?(?=$|[\s,.?!])"
# 띄어 쓴 호칭(`"김도윤 고객님"`·`"그 김민준 씨가"`)과 붙여 쓴 「님」(`"홍길동님"`)을 나눠 본다 — 한 정규식에 합치면
# `"김도윤 고객님"` 을 「김도윤 고객」+「님」 두 어절 이름으로 읽는다(실제로 그랬다)
_HONORIFIC_SPACED = re.compile(
    r"(?:^|(?<=[\s,.?!]))(?P<name>[가-힣]{2,4}(?:\s[가-힣]{2,4})?)\s(?:고객님|선생님|씨)" + _AFTER_HONORIFIC
)
_HONORIFIC_ATTACHED = re.compile(r"(?:^|(?<=[\s,.?!]))(?P<name>[가-힣]{3})(?:씨|님)" + _AFTER_HONORIFIC)
# 「이예요」 는 맞춤법이 틀린 모양이지만 실제 발화(STT·채팅)에 흔하다 — `"인천이예요"` 를 「인천이」+「예요」 로 읽던 것을 막는다
_SHORT_ANSWER_ENDINGS = ("이에요", "이예요", "이고요", "인데요", "입니다", "이요", "예요", "요")
_SENTENCE_START = re.compile(r"(?:^|(?<=[.?!]\s))(?P<tok>[가-힣]{3,8})(?=[.?!,]?(?:\s|$))")

# 성씨로 시작하지만 이름이 아닌 말 · 문맥 뒤에 오지만 이름이 아닌 말. **실제로 걸린 것만** 넣는다 — 추측으로 늘리면
# 진짜 이름을 놓친다(누락 0건이 과잉 억제보다 앞선다).
_NOT_NAMES = frozenset((
    # 문맥 뒤(AI Hub 실제 발화 · 합성 통화)
    "변경", "어떻게", "뭐", "무엇", "확인", "정정", "등록", "기재", "이전", "도용", "동일", "같은", "다른",
    "말씀", "알려", "적어", "좀", "혹시", "그리고", "그러면", "이렇게", "그렇게", "여기", "거기", "누구", "어디",
    "맞아요", "맞습니다", "본인", "대리인", "신청인", "고객", "성명", "신분증", "서류", "주소", "연락처", "번호",
    "한국인", "외국인", "학생", "주부", "직장인", "세입자", "집주인", "보호자", "세대주", "세대원", "공무원",
    # 호칭 앞(성씨로 시작하는 보통 명사·대명사)
    "우리", "저희", "이분", "그분", "해당", "모든", "여러", "담당", "담당자", "상담", "상담원", "기사", "선생",
    "사장", "부장", "과장", "팀장", "원장", "교수", "의사", "간호사", "민원", "민원인", "신청", "대리", "보호",
    "고령", "장애", "이번", "다음", "기존", "신규", "방문", "어머", "아버", "부모", "형", "누", "언니", "오빠",
    "사모", "주인", "관리", "관리자", "위원", "회원", "조합원", "소장", "구청장", "시장", "동장", "반장",
    # 이름만 답한 발화 자리
    "정확히", "조금만", "고마워", "안녕하", "감사해", "이거는", "이것도", "여기는", "여기서", "오늘은", "지금은",
    "진짜로", "전화로", "전부다", "어제는", "내일은", "이번엔", "그거는", "주소는", "전화는", "정말로", "고맙습",
    "수고하", "알겠어", "알겠습", "이따가", "조금요", "나중에", "금방요", "한번만", "안되나", "없어요", "있어요",
    # 1차 보강 뒤 실제 발화 재측정에서 걸린 것
    "성함", "이름", "명의", "명의자", "어느분", "어느", "어떤분", "누구신지", "배우자", "가족분", "남편분", "아드님",
    "따님", "어머님", "아버님", "할머님", "할아버님", "지하철", "어떤거",
    "신고자", "제보자", "조부모", "이메일", "현재", "노래방", "편의점",
    # 2026-09-18 합성 대본 24건·가족 호칭 문맥에서 걸린 것
    "고객님", "선택은", "장애인", "임산부", "고령자", "유공자",
))
# 이름이 이렇게 끝나지 않는다 — 서술·관형 어미(`"친근하네"`·`"다른가"`·`"하는데"`)
_NOT_NAME_TAILS = ("하네", "네", "는가", "른가", "인가", "은가", "던것", "는데", "에", "되면", "르면", "으면", "주신", "해본")
# 장소 접미사(`"기흥역"`·`"신월동"`·`"도봉구"`) — **이름만 답한 발화에만** 쓴다. 문맥·호칭 뒤에서는 `"홍길동"`·`"김소리"` 처럼
# 진짜 이름이 이렇게 끝난다(첫 판이 전부에 걸어 두 이름을 놓쳤다). 「호·원·도」 는 여기에도 넣지 않는다 — `"박성호"`
_PLACE_TAILS = ("역", "동", "구", "군", "읍", "면", "리", "점", "층", "길", "방")
_NOT_NAME_PREFIXES = ("변경", "확인", "정정", "등록", "기재", "변동", "바꾸", "바꿔", "수정", "신청", "발급", "문의",
                      "알려", "입력", "말씀", "적어", "불러", "여쭤", "확인해")

# 동사·형용사 어미로 끝나는 덩어리는 이름이 아니다 — 문맥 뒤 긴 덩어리(5자 이상)를 어절째 가릴 때만 본다
_VERBAL_TAILS = ("려면", "려고", "하고", "해서", "하는", "해요", "합니다", "하면", "해야", "했어", "할게", "세요",
                 "나요", "까요", "죠", "니다", "는데", "어요", "아요", "지요", "거든")


# 호칭 앞에서 이름이 아니라 수식어로 끝나는 모양. 「은·는」 은 넣지 않는다 — `"김지은 고객님"` 이 끝이 「은」 이다
_MODIFIER_TAILS = ("의", "에게", "많은", "적은", "같은", "모든", "다른", "하는", "했던", "보다")


def _strip_particles(name: str) -> str:
    """뒤에 붙은 조사를 벗긴다. 한 번만 벗긴다 — 두 번 벗기면 이름 글자를 먹는다."""
    for p in _PARTICLES:
        if len(name) - len(p) >= 1 and name.endswith(p):
            return name[: -len(p)]
    return name


def _starts_with_surname(word: str) -> bool:
    return word[:2] in _SURNAMES_2 or word[:1] in _SURNAMES_1


def _is_not_name(word: str) -> bool:
    return word in _NOT_NAMES or word.startswith(_NOT_NAME_PREFIXES) or word.endswith(_NOT_NAME_TAILS)


def _span(start: int, length: int) -> PiiSpan:
    return PiiSpan(pattern="P6", start=start, end=start + length)


def _after_context(text: str, pos: int) -> list[PiiSpan]:
    """문맥 뒤 최대 세 어절. 조사가 붙은 어절에서 멈춘다(`"박서연이고 번호는"`)."""
    # 공백 하나로만 이어진 한글 어절 최대 세 개 — 쉼표·마침표에서 끊는다
    tokens = []
    for m in re.finditer(r"[가-힣]+", text[pos:]):
        start = pos + m.start()
        prev_end = tokens[-1][0] + len(tokens[-1][1]) if tokens else pos
        if len(tokens) == 3 or (tokens and text[prev_end:start] != " "):
            break
        tokens.append((start, m.group()))

    found: list[PiiSpan] = []
    for i, (start, raw) in enumerate(tokens):
        name = _strip_particles(raw)
        if _is_not_name(name) or (i > 0 and raw.endswith(_VERBAL_TAILS)):
            break
        if i == 0 and len(name) >= 5 and (raw.endswith(_VERBAL_TAILS) or len(name) > 8):
            break  # 긴 덩어리는 어절째 가리되(GS-037) 동사 어미면 이름이 아니다
        found.append(_span(start, len(name)))
        if name != raw:
            break  # 조사가 붙은 어절에서 이름이 끝난다(`"박서연이고 번호는"`)
    # 첫 어절이 한 글자면 이름이 아니다(`"이름이나 나이는"` 의 「나」 · `"이름은 잘 기억"` 의 「잘」) — 한 글자 조각(`"티"`)은
    # 여러 어절 외국인 이름의 **가운데**에서만 나온다
    if not found or found[0].length < 2:
        return []
    return found


def _context_names(text: str) -> list[PiiSpan]:
    found: list[PiiSpan] = []
    for m in _CONTEXT.finditer(text):
        found += _after_context(text, m.end())
    for m in list(_SELF_INTRO.finditer(text)) + list(_FAMILY_INTRO.finditer(text)):
        span = _introduced_name(text, m.end())
        if span is not None:
            found.append(span)
    return found


def _introduced_name(text: str, pos: int) -> PiiSpan | None:
    """「저는」·「아버지는」 뒤 어절이 이름을 밝히는 어미로 끝나면 그 이름. 성씨 포함 3자(복성 4자)만 —
    `"저는 강남구요"`·`"저는 서울시민이고요"` 를 이름으로 보지 않는다(짧은 답 규칙과 같은 기준)."""
    tok = re.match(r"[가-힣]{3,10}", text[pos:])
    if tok is None:
        return None
    ending = next((e for e in _INTRO_ENDINGS if tok.group().endswith(e)), None)
    if ending is None:
        return None
    name = tok.group()[: -len(ending)]
    want = 4 if name[:2] in _SURNAMES_2 else 3
    place = name.endswith(_PLACE_TAILS) or name.startswith(WIDE_AREA_NAMES)
    if len(name) == want and _starts_with_surname(name) and not _is_not_name(name) and not place:
        return _span(pos, len(name))
    return None


def _honorific_names(text: str) -> list[PiiSpan]:
    found: list[PiiSpan] = []
    matches = list(_HONORIFIC_SPACED.finditer(text)) + list(_HONORIFIC_ATTACHED.finditer(text))
    for m in matches:
        words = m.group("name").split(" ")
        start = m.start("name")
        if any(w.endswith(_MODIFIER_TAILS) for w in words):
            continue  # `"2명 이상의 고객님"`·`"보다 많은 고객님"` — 호칭 앞 수식어다
        if len(words) == 1:
            word = words[0]
            # 한 어절 호칭은 성씨 포함 3자(복성 4자)만 — `"전화주신 고객님"` 같은 4자 서술어를 막는다. 2자는 흔한 명사가 더 많다
            want = 4 if word[:2] in _SURNAMES_2 else 3
            if len(word) == want and _starts_with_surname(word) and not _is_not_name(word):
                found.append(_span(start, len(word)))
            continue
        # 두 어절 — 외국인 이름(`"제니 레예스 고객님"`). 성씨 검사를 할 수 없으니 **문장 첫머리**일 때만 받는다
        before = text[:start].rstrip()
        # 외국인 이름 어절은 한국어 조사·어미로 끝나지 않는다(`"요금이 체납되면 고객님"` 을 막는다).
        # 둘째 어절에서는 「이」 를 빼고 본다 — `"다나카 유이 고객님"`(SYN-017) 처럼 이름이 「이」 로 끝난다. 첫 어절의 「이」 는 주격 조사다
        _tails = ("이", "가", "은", "는", "을", "를", "면", "고", "서", "도", "로", "요", "다", "과", "와", "본", "신")
        korean_tail = words[0].endswith(_tails) or words[1].endswith(_tails[1:]) or len(words[0]) < 2
        if (before == "" or before.endswith((",", ".", "?", "!", "네"))) and not korean_tail and not any(_is_not_name(w) for w in words):
            found.append(_span(start, len(words[0])))
            found.append(_span(start + len(words[0]) + 1, len(words[1])))
        elif (len(words[1]) == (4 if words[1][:2] in _SURNAMES_2 else 3)
              and _starts_with_surname(words[1]) and not _is_not_name(words[1])):
            # `"그 김민준 씨"` 의 「그」 는 이름이 아니다. 한 어절 호칭과 같은 길이 기준 — `"신청은 위임장과 고객님"` 의 「위임장과」(SYN-020)
            found.append(_span(start + len(words[0]) + 1, len(words[1])))
    return found


def _short_answer_names(text: str) -> list[PiiSpan]:
    found: list[PiiSpan] = []
    for m in _SENTENCE_START.finditer(text):
        tok = m.group("tok")
        if text[m.end("tok"):m.end("tok") + 1] == "?":
            continue  # 되묻는 말(`"예배는요?"`·`"어떤거요?"`)은 이름을 답한 게 아니다
        ending = next((e for e in _SHORT_ANSWER_ENDINGS if tok.endswith(e)), None)
        if ending is None:
            continue
        name = tok[: -len(ending)]  # 가장 먼저 맞는 어미 하나만 — `"민원이요"` 를 「민원이」+「요」 로 다시 보지 않는다
        want = 4 if name[:2] in _SURNAMES_2 else 3
        place = name.endswith(_PLACE_TAILS) or name.startswith(WIDE_AREA_NAMES)  # `"도봉구인데요"`·`"경기도입니다"`
        if len(name) == want and _starts_with_surname(name) and not _is_not_name(name) and not place:
            found.append(_span(m.start("tok"), len(name)))
    return found


def detect_names(text: str) -> list[PiiSpan]:
    """P6 구간 목록. 문맥·자기소개·호칭·이름만 답한 발화에서만 잡는다 — 일반 NER 을 대체하지 않는다."""
    return _context_names(text) + _honorific_names(text) + _short_answer_names(text)
