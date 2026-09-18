# Requirement: C-5, QUA-1
"""2026-09-18 합성 통화 E2E 24건·대시보드 화면에서 드러난 C-5 구멍 — 누락·오분류·과잉을 한 파일에 고정한다.

출처는 둘이다. 문장을 지어내지 않고 실제로 걸린 모양을 옮겼다.
- 합성 대본 `scripts/persona_sim/dasan-v0` (SYN-011~021) — 자막·DB 에 이름이 원문으로 남았다(SEC-1)
- AI Hub 민원 질의응답(validation 다산) 실제 발화 — 규칙을 넓힌 뒤 새로 잘못 가린 조각

09-17 파일(`test_pii_gaps_0917.py`)과 같은 이유로 **두 방향을 같이 본다** — 누락만 보면 「전부 가린다」가 만점이다.
"""

import pytest

from masking.domain.services.masker import mask_text


def _masked(text):
    return mask_text(text)[0]


def _patterns(text):
    return [s.pattern for s in mask_text(text)[1]]


# ── P6 누락 — SYN-020 #16 ───────────────────────────────────────────────────

@pytest.mark.parametrize("text, names", [
    ("저는 강민재고요, 아버지는 강영식이에요. 연락처는 010-0000-0120입니다.", ["강민재", "강영식"]),  # 모음 끝 이름+「고요」 · 가족 호칭
    ("저는 김수아고요 대신 신청하러 왔어요", ["김수아"]),
    ("저는 이도윤구요", ["이도윤"]),
    ("어머니는 박정순이에요", ["박정순"]),
    ("아버님이 최영수입니다", ["최영수"]),
    ("남편은 정우진이고요, 저는 한지민이에요", ["정우진", "한지민"]),
    ("아들이 김민준예요", ["김민준"]),
])
def test_P6_자기소개_어미와_가족_호칭_뒤_이름을_잡는다(text, names):
    masked = _masked(text)
    for name in names:
        assert name not in masked, f"「{name}」 이 남았다: {masked}"
    assert "P6" in _patterns(text)


def test_P6_이름_뒤_말투는_남긴다():
    assert _masked("저는 강민재고요, 아버지는 강영식이에요.") == "저는 ***고요, 아버지는 ***이에요."


# ── P6 과잉 — 가족 호칭·자기소개 뒤에 오지만 이름이 아닌 말 ────────────────

@pytest.mark.parametrize("text", [
    "아버지는 다리가 안 좋으셔서 제가 대신 만들어 드리려고요.",   # SYN-020 #2
    "아버지가 장애인이에요",
    "어머니는 세대주예요",
    "아들은 대학생이에요",
    "저는 괜찮고요, 어머니가 걱정이에요",
    "저는 강남구요",                                            # 2자 — 이름으로 안 본다
    "저는 서울시민이고요",
    "어머니는 임산부예요",
])
def test_P6_가족_호칭_뒤_보통명사는_남긴다(text):
    assert "P6" not in _patterns(text), _masked(text)


# ── P6 과잉 — 합성 대본에서 이름으로 잘못 가린 것 ────────────────────────────

@pytest.mark.parametrize("text, piece", [
    ("네. 도서관 회원 카드, 누가 쓰나요? 고객님이요, 아이요?", "고객님"),                       # SYN-017 #5
    ("다만 납세자와 계좌 명의자가 다르면 위임장과 계좌 명의자 신분증이 추가로 필요합니다.", "다르면 위임장과 계좌"),  # SYN-019 #5
    ("둘 다 대리 신청은 위임장과 고객님 신분증이 필요합니다.", "위임장과"),                     # SYN-020 #19
    ("그런 제도가 있다는 안내입니다. 선택은 고객님이 하시면 됩니다.", "선택은"),                # SYN-012 #15
])
def test_P6_대본에서_잘못_가린_조각을_남긴다(text, piece):
    assert piece in _masked(text)


def test_P6_호칭_앞_진짜_이름은_그대로_잡는다():
    """과잉을 줄이느라 09-17 이 잡던 것을 놓치면 안 된다."""
    assert "김민준" not in _masked("그 김민준 씨가 어제 전화했었는데요")
    assert "김지은" not in _masked("네, 김지은 고객님. 신분증 챙기세요.")
    assert _masked("네, 다나카 유이 고객님. 정리할게요.").startswith("네, *** ** 고객님")  # SYN-017 #13 — 「이」 로 끝나는 외국인 이름


# ── P4 오분류 — 한글 수사 휴대전화 뒤 「이에요」 ─────────────────────────────

@pytest.mark.parametrize("text", [
    "공일공 공공공공 공일일육이에요. 문자로 주시면 좋겠어요.",  # SYN-016 #12 — 「이」 가 2 로 붙어 12자리 계좌로 읽혔다
    "공일공 공공공공 공일일일이에요",
    "공일공 공공공공 공일이일이요",
])
def test_P4_한글_수사_휴대전화는_뒤_조사가_붙어도_P4다(text):
    patterns = _patterns(text)
    assert "P4" in patterns and "P3" not in patterns, patterns
    assert "공일공" not in _masked(text)


def test_P4_한글_수사_뒤_이_는_가려도_된다():
    """라벨만 바로잡는다 — 구간은 넓은 쪽을 남긴다(누락 0건 > 과잉 억제). 「이」 한 글자가 더 가려지는 것은 감수한다."""
    masked = _masked("공일공 공공공공 공일일육이에요")
    assert masked.endswith("에요")
