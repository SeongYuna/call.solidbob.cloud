# Requirement: D-1, D-2, E-1, QUA-1
"""D-1·D-2 규칙 채점기(`metrics/postcall.py`) — 포함·동의 표기·정규화·누락·유형 null 처리. 모델을 부르지 않는다(절대 원칙 1)."""

from __future__ import annotations

import pytest

from evaluation.metrics.postcall import (
    TYPE_NULL,
    KeyItem,
    PostcallCase,
    item_present,
    normalize,
    score_call,
    score_postcall,
)

DOC = KeyItem(id="c.doc", kind="서류", label="세대주 확인서", forms=("세대주 확인서", "남편분 신분증"))
INQ = KeyItem(id="c.inq", kind="문의", label="전입신고", forms=("전입신고",))
ACT = KeyItem(id="c.act", kind="조치", label="다시 안내", forms=("다시 안내드리겠습니다",))


def _case(summary: str, predicted_type: str | None = None, items=(INQ, DOC, ACT)) -> PostcallCase:
    return PostcallCase(call_id="c", key_items=tuple(items), expected_type="일반행정 문의",
                        summary=summary, predicted_type=predicted_type)


def test_정규화는_공백_문장부호_가림문자를_지우고_소문자로():
    assert normalize("전입 신고, (세대주)!") == "전입신고세대주"
    assert normalize("010-****-1234") == "0101234"
    assert normalize("ARC 등록증") == "arc등록증"


def test_허용_표기가_글자로_있으면_포함이다():
    assert item_present("고객 문의: 전입신고 해야 돼요?", INQ)


def test_동의_표기_중_하나만_있어도_포함이다():
    assert item_present("남편분 신분증을 가져오세요", DOC)
    assert item_present("세대주 확인서", DOC)


def test_띄어쓰기_문장부호가_달라도_포함이다():
    assert item_present("전입 신고를 하셔야 해요", INQ)
    assert item_present("세대주-확인서.", DOC)


def test_허용_표기에_없는_바꿔말하기는_놓친다():
    # 한계를 고정한다 — 포함률은 하한이다
    assert not item_present("주소 이전 신고를 하셔야 해요", INQ)


def test_통화_하나의_포함률과_놓친_항목():
    s = score_call(_case("고객 문의: 전입신고 / 상담원 안내: 남편분 신분증"))
    assert s.hit == ("c.inq", "c.doc")
    assert s.missed == ("c.act",)
    assert s.missed_labels == ("다시 안내",)
    assert s.coverage == pytest.approx(2 / 3)


def test_아무것도_없으면_0이다():
    assert score_call(_case("발화 고객 1건 · 상담원 1건 (규칙 발췌 초안)")).coverage == 0.0


def test_매크로는_통화마다_같은_무게_마이크로는_항목마다():
    a = _case("전입신고 남편분 신분증 다시 안내드리겠습니다")  # 3/3
    b = PostcallCase(call_id="d", key_items=(INQ,), expected_type="일반행정 문의", summary="없음", predicted_type=None)  # 0/1
    r = score_postcall([a, b])
    assert r["n_calls"] == 2 and r["key_items"] == 4 and r["key_items_hit"] == 3
    assert r["coverage_macro"] == pytest.approx(0.5)
    assert r["coverage_micro"] == pytest.approx(0.75)
    assert r["per_call"] == {"c": 1.0, "d": 0.0}
    assert r["missed"] == {"d": ["전입신고"]}
    assert r["coverage_by_kind"] == {"문의": "1/2", "서류": "1/1", "조치": "1/1"}


def test_유형이_전부_None_이면_0점이_아니라_측정_불가다():
    r = score_postcall([_case("전입신고", None), _case("전입신고", None)])
    assert r["type_accuracy"] == TYPE_NULL
    assert "type_null" not in r


def test_유형은_글자까지_같아야_맞고_None_은_분모에_남는다():
    r = score_postcall([_case("x", "일반행정 문의"), _case("x", "일반행정"), _case("x", None)])
    assert r["type_accuracy"] == pytest.approx(1 / 3)
    assert r["type_null"] == 1


def test_빈_입력은_채점하지_않는다():
    with pytest.raises(ValueError):
        score_postcall([])


def test_빈_표기는_거부한다():
    with pytest.raises(ValueError):
        KeyItem(id="x", kind="서류", label="x", forms=())
    with pytest.raises(ValueError):
        KeyItem(id="x", kind="서류", label="x", forms=(" , ",))  # 정규화하면 빈 문자열 — 모든 요약에 걸린다
