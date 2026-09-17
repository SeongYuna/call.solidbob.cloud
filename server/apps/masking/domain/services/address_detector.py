# Requirement: C-5
"""탐지 파이프라인 ③ 확장 — P7 상세주소.

[2.4절](/docs/02/)은 P7 을 **NER** 로 적었지만, 확보한 데이터셋에 주소 태그가 없어
학습·평가가 불가능하다([미결 항목](/open-items/)). 그래서 **규칙으로 먼저 바닥을 깐다** —
0% 로 두는 것보다 낫고, 「누락 0건 > 과잉 마스킹 억제」 원칙에도 맞는다.
NER 이 붙으면 이 규칙은 폴백으로 남는다.

**토큰 연속성으로 잡는다.** 주소는 행정구역이 큰 단위에서 작은 단위로 이어지는
연속된 어절이다. 한 토큰만 보고 판단하면 "새로"·"그러므로" 같은 일상어의 `로` 에
걸린다 — **2어절 이상 이어지고 행정구역 표지가 하나라도 있을 때만** 주소로 본다.

**2026-09-17 보강 — 두 방향.**
- 누락: 도로명 뒤 **건물번호**(`"은하로 7-3"`·`"햇살로 45, 102동"`·`"정릉로 77길 12에서"`)가 표지 없는 숫자라 run 이 끊겨
  번지가 자막·DB 에 남았다(합성 통화 E2E · 골든셋 GS-415). 도로명(또는 `77길`) **바로 뒤**의 숫자만 건물번호로 받는다.
- 과잉: 어미·조사가 행정구역 접미사처럼 생겼다 — `"하시면"`(면) · `"혹시"·"다시"`(시) · `"신분증으로"`(로).
  AI Hub 실제 발화 20,278건에서 459건이 P6·P7 로 가려졌고 상위가 전부 이것이었다. 어간 길이와 어미로 거른다.
"""

from __future__ import annotations

import re

from ..value_objects.pii_pattern import PiiSpan

# 광역단체는 **닫힌 목록**으로 둔다. `도` 를 접미로 열어두면 `"보내도"`·`"어디로 보내도"` 같은
# 어미가 전부 주소가 된다(실제로 걸렸다). 광역단체는 17개뿐이라 열거가 정확하고 싸다.
_WIDE_NAMES = ("서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기",
               "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
               "충청북", "충청남", "전라북", "전라남", "경상북", "경상남")
WIDE_AREA_NAMES = _WIDE_NAMES  # 이름 규칙이 「경기도입니다」 를 이름으로 보지 않게 빌려 쓴다
_AREA_WIDE = re.compile(
    r"^(?:%s)(?:특별시|광역시|특별자치시|특별자치도|시|도)?$" % "|".join(_WIDE_NAMES))
# 기초단체·법정동. `도` 는 위에서만 인정한다. 한 글자 동네(`우동`)를 살리려 {1,10} 이지만,
# 어절이 2개 이상 이어져야 주소로 보므로 `"운동 하세요"` 는 걸리지 않는다.
_AREA_LOCAL = re.compile(r"^(?P<stem>[가-힣]{1,10})(시|군|구|읍|면|동|리)$")
# 한 글자 어간을 허용하는 것은 방위 구(`중구`·`북구`)와 동(`우동`) 뿐이다 — `"혹시"·"다시"·"처리"·"자동"·"친구"` 가 전부 한 글자 어간이다
_ONE_SYLLABLE_OK = {"구": set("중동서남북"), "동": set("우")}
# 「면」 앞 글자가 이것이면 어미다(`"하시면"`·`"정리하면"`·`"어려우시면"`·`"발급하시려면"`·`"자양동이면"`)
_VERBAL_BEFORE_MYEON = set("하시으려다라되보가오주나내지기우치키추두르서터이리러니드께거어아게")
# 행정구역처럼 생긴 보통 명사(실제 발화에서 걸린 것만)
_LOCAL_NOT_AREA = {"지역구", "선거구", "관할구", "행정구", "홍대입구"}
# 「~할 때」 의 「시」(`"승차시"`·`"이동시"`·`"결제시"`) — 한자어 동작 명사 뒤에 붙는다. 실제로 걸린 것과 같은 갈래만 둔다
_WHEN_SI = re.compile(r"(승차|하차|환승|이동|결제|이용|신청|접수|방문|도착|출발|발급|납부|확인|변경|입력|조회|필요|초과|미납|연체|분실|위반|적발|탑승|주차|정차|운행|통행|택)시$")
# 도로명. `로`·`길` 은 일상어에도 흔해 단독으로는 신호가 약하다.
_ROAD = re.compile(r"^[가-힣]{2,10}(대로|로|길)$")
# `"으로"` 로 끝나는 도로명은 없다 — 조사다(`"신분증으로"`·`"인터넷으로"`). 부서·기관 뒤 `로` 도 조사다(`"교통지도과로"`)
_ROAD_NOT = re.compile(r"(으로|과로|센터로|소로|처로|팀로|"
                       r"(버스|지하철|택시|콜택시|도보|뒷차|차|셔틀|카드|팩스|문자|메일|전화|현금|계좌|최단거리|거리|방향|기차|자전거|우편)로)$")
# `"77길"`·`"3로"` — 숫자로 된 도로명 가지. 도로명 바로 뒤에서만 받는다
_ROAD_NUM = re.compile(r"^\d+(번?길|로)")
# 번지·호·층·동. 숫자로 시작하므로 오탐이 적고, 주소의 끝을 알려준다.
_NUMBERED = re.compile(r"^\d+(번지|호(?!선)|층|동|가)")  # 「1호선」 은 지하철 노선이다
# 건물번호 — 표지 없는 숫자(`"45,"`·`"7-3"`·`"12에서"`). **도로명 바로 뒤에서만** 받는다(아무 숫자나 주소가 되지 않게)
# 단위가 붙은 숫자(`"194m"`·`"14분"`·`"5만원"`·`"6개월"`·`"10명"`)는 건물번호가 아니다 — 실제 발화에서 「도보로 194m」 를 주소로 잡았다
_BUILDING = re.compile(r"^\d+(?:-\d+)?(?!\d|\.\d|m|k|M|K|분|만|천|개|명|원|시|년|월|일|번|회|대|%|키로|미터|정거장|세|살|인|건|장|권|배|위|등|초|주|호선|차|석|평|층|호|동)")


def _is_local(token: str) -> bool:
    m = _AREA_LOCAL.match(token)
    if not m or token in _LOCAL_NOT_AREA or _WHEN_SI.search(token) or token.endswith("방면"):
        return False
    stem, suffix = m.group("stem"), token[-1]
    if len(stem) == 1 and stem not in _ONE_SYLLABLE_OK.get(suffix, ()):
        return False
    return not (suffix == "면" and stem[-1] in _VERBAL_BEFORE_MYEON)


def _is_road(token: str) -> bool:
    return bool(_ROAD.match(token)) and not _ROAD_NOT.search(token)


def _kind(token: str, prev: str | None) -> str | None:
    """어절의 주소 성분. 건물번호·숫자 도로명은 **바로 앞이 도로명일 때만** 성분이 된다."""
    bare = token.rstrip(",.")
    if _AREA_WIDE.match(bare):
        return "wide"
    if _is_local(bare):
        return "local"
    if _NUMBERED.match(token):
        return "numbered"
    if prev == "road" and _ROAD_NUM.match(token):
        return "road"
    if _is_road(bare):
        return "road"
    if prev == "road" and _BUILDING.match(token):
        return "building"
    return None


# 행정구역 표지 — 이것이 하나도 없으면 주소로 보지 않는다(`로`·`길` 만으로는 약하다).
# 건물번호는 도로명 뒤에서만 나오므로 「도로명 + 건물번호」 자체가 표지다
_STRONG = {"wide", "local", "numbered", "building"}


def _tokens(text: str) -> list[tuple[int, str]]:
    """(시작 오프셋, 토큰). 문자 오프셋이므로 한글이 섞여도 어긋나지 않는다."""
    return [(m.start(), m.group()) for m in re.finditer(r"\S+", text)]


def _trim_tail(token: str) -> int:
    """마지막 토큰에 붙은 조사를 잘라낸다.

    `"456호예요"` 에서 `"예요"` 까지 가리면 자막이 `"456호***"` 처럼 읽히지 않는다.
    번호 뒤 조사가 번호에 먹히던 문제(한글 수사)와 같은 종류다.
    """
    m = _NUMBERED.match(token) or _ROAD_NUM.match(token) or _BUILDING.match(token)
    if m:
        return m.end()
    bare = token.rstrip(",.")
    m = _AREA_WIDE.match(bare) or _AREA_LOCAL.match(bare) or _ROAD.match(bare)
    return m.end() if m else len(token)


def detect_addresses(text: str) -> list[PiiSpan]:
    """P7 구간 목록. 주소 어절이 2개 이상 이어지고 행정구역 표지가 있을 때만 잡는다."""
    tokens = _tokens(text)
    found: list[PiiSpan] = []

    run: list[tuple[int, str, str]] = []
    for offset, token in tokens + [(-1, "")]:          # 보초값으로 마지막 run 을 닫는다
        kind = _kind(token, run[-1][2] if run else None) if offset >= 0 else None
        # 쉼표·마침표가 붙은 어절(`"45,"`)은 성분이지만, 조사가 붙은 건물번호(`"12에서"`)는 주소의 끝이다
        if kind is not None:
            run.append((offset, token, kind))
            if not (kind == "building" and token.rstrip(",.") != _BUILDING.match(token).group()):
                continue
            token, offset = "", -2                     # 이 어절에서 run 을 닫는다
        if len(run) >= 2 and any(k in _STRONG for _, _, k in run):
            start = run[0][0]
            last_offset, last_token, _ = run[-1]
            found.append(PiiSpan(pattern="P7", start=start,
                                 end=last_offset + _trim_tail(last_token)))
        run = []
        # 방금 run 을 끊은 어절이 새 run 의 첫 성분일 수 있다(`"그러면 서울시 강남구"`)
        if offset >= 0:
            kind = _kind(token, None)
            if kind is not None:
                run.append((offset, token, kind))
    return found
