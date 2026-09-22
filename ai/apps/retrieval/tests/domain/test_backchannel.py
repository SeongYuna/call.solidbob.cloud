# Requirement: B-1, B-6
"""맞장구·인사·감사·끝인사 판정(`decisions/216`). 순수 규칙이라 외부 자원 없이 돈다."""

from __future__ import annotations

import pytest

from retrieval.domain.services.backchannel import BACKCHANNEL_UNITS, is_backchannel, normalize


@pytest.mark.parametrize(
    "text",
    [
        "네", "네.", "예", "네네", "네 네 네",
        "아 네, 알겠습니다.", "아네알겠습니다", "아  네 ,  알겠 습니다 !!",
        "감사합니다", "감사합니다!", "네, 감사합니다.", "정말 감사합니다~",
        "수고하세요", "수고하셨습니다.", "안녕하세요", "여보세요?",
        "알겠어요", "네 알겠어요, 감사합니다!", "그래요", "아하", "음...", "...네.",
        "네, 이해했습니다.", "안녕히 계세요", "좋은 하루 되세요",
    ],
)
def test_맞장구로만_된_발화(text):
    assert is_backchannel(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "네, 그런데 초본은요?",               # 맞장구 + 질문 — 발동해야 한다
        "아 네, 그럼 뭘 가져가야 되는데요?",
        "초본이요",
        "감사합니다. 그런데 위임장은 누가 써요?",
        "네 알겠습니다 신청은 어디서 해요",
        "알겠는데요",                         # 「는데요」 — 말이 이어진다
        "네 5",                               # 숫자가 남는다
        "과태료",
        "여권도 돼요?",
    ],
)
def test_내용이_남으면_맞장구가_아니다(text):
    assert is_backchannel(text) is False


@pytest.mark.parametrize("text", ["***이요.", "네 ***", "네, *** 입니다", "*****"])
def test_가림이_있으면_맞장구로_보지_않는다(text):
    """가려진 자리에 무엇이 있었는지 모른다 — 「네 ***」 를 「네」 로 읽지 않는다(B 는 재현율 우선)."""
    assert is_backchannel(text) is False


@pytest.mark.parametrize("text", ["", "   ", "...", "?!"])
def test_정규화해_비면_이_규칙의_범위_밖이다(text):
    assert is_backchannel(text) is False


def test_정규화는_문장부호와_공백을_지운다():
    assert normalize(" 아 네,  알겠 습니다!! ") == "아네알겠습니다"


def test_어휘에는_점수나_숫자가_없다():
    """숫자 문턱을 두지 않는다 — 어휘 단위는 전부 한글이다."""
    assert all(u and all("가" <= ch <= "힣" for ch in u) for u in BACKCHANNEL_UNITS)
