# Requirement: C-6
"""C-6 판정 규칙. **재현율 우선**이지만 `distress` 오분류와 과탐지는 따로 잡는다.

⚠ **이 테스트와 골든셋 C-6 케이스를 같은 사람이 만들었다**(2026-09-09, 류준).
`golden-set/README.md` 가 F-2 에 대해 경고한 자기충족 문제가 여기에도 그대로 걸린다 —
여기서 나오는 재현율·정밀도는 **상한**이지 실제 성능이 아니다. 교차검수가 필요하다.
"""

from __future__ import annotations

import pytest

from call_guard.domain.services.detector import detect


def _cats(text: str) -> list[str]:
    return [d.category for d in detect(text)]


# ── 갈래별 탐지 ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("text", [
    "야 이 씨발 놈아 일을 그따위로 하냐",
    "너 지금 장난하냐 이 개새끼야",
    "말귀를 못 알아듣네 병신같이",
])
def test_욕설은_사전으로_잡는다(text):
    assert "insult" in _cats(text)


@pytest.mark.parametrize("text", [
    "머리에 뭐가 들었길래 그것도 하나 처리를 못 해",
    "됐고 그냥 시장 나오라 그래 이 인간들아",
])
def test_욕설_없는_인격_모독도_잡는다(text):
    """5.2 조가 「반복되는 인격 모독」을 종료 사유로 두는데 대부분이 욕설이 아니다.
    사전만 있으면 이 구간이 통째로 비어 재현율이 구조적으로 막힌다."""
    assert "insult" in _cats(text)


@pytest.mark.parametrize("text", [
    "당신 이름 뭐야 내가 찾아가서 가만 안 둘 거야",
    "거기 몇 층이야 지금 그리로 갈 테니까 기다려",
])
def test_위협을_잡는다(text):
    assert "threat" in _cats(text)


def test_성적_표현을_잡는다():
    assert "sexual" in _cats("목소리 들어보니까 아가씨인가 본데 얼굴 한번 봅시다")


# ── distress — 폭언과 다르게 다뤄야 하는 갈래 ────────────────────────────
@pytest.mark.parametrize("text", [
    "진짜 다 필요없고 그냥 죽어버리고 싶어요",
    "이렇게 사느니 그냥 확 끝내버릴까 싶네요",
    "이제 살 이유가 없는 것 같아요",
])
def test_위기_신호를_잡는다(text):
    assert "distress" in _cats(text)


@pytest.mark.parametrize("text", [
    "죽겠네 진짜 하루 종일 전화만 붙잡고 있으니",
    "아 배고파 죽겠어요",
    "기다리다가 죽을 맛이네요",
])
def test_관용_표현은_위기_신호가_아니다(text):
    """「죽겠다」는 힘듦을 나타내는 관용 표현이다. 이걸 잡으면 전문 기관 연결이
    남발되고, 정작 진짜 위기 때 상담원이 경고를 무시하게 된다."""
    assert "distress" not in _cats(text)


def test_위해_표현과_겹치면_위기를_남긴다():
    """5.2 조(즉시 종료)와 5.4 조(끊지 않고 연결)의 대응이 **정반대**다.
    잘못 고르면 위기 상황에서 전화를 끊는다."""
    cats = _cats("다 필요 없어요 그냥 죽어버리고 싶어요")
    assert cats and cats[0] == "distress"


# ── 정상 발화 — 여기가 정밀도를 만든다 ───────────────────────────────────
@pytest.mark.parametrize("text", [
    "아니 이런 식으로 하면 안 되죠 진짜 말이 안 되잖아요",
    "아 진짜 짜증나네 몇 번을 전화해야 되는 거예요",
    "담당자 바꿔주세요 이건 말이 안 되는 거 같은데",
    "아까부터 계속 기다렸는데 아직도 안 되나요",
    "전에 전화했을 때랑 말이 다르잖아요 누구 말을 믿어야 하나요",
    "필요한 서류가 뭐가 있는지 알려주세요",
])
def test_강한_항의는_폭언이_아니다(text):
    """재현율만 보고 만들면 「전부 폭언」이라고 답하는 구현이 만점을 받는다(절대 원칙 10)."""
    assert detect(text) == []


def test_빈_발화는_빈_목록이다():
    assert detect("") == [] and detect("   ") == []


# ── 결과 형태 ────────────────────────────────────────────────────────────
def test_걸린_표현은_원문에서_잘라낸다():
    """사전 항목이나 정규식을 그대로 돌려주면 화면에 정규식이 뜬다."""
    text = "당신 이름 뭐야 내가 찾아가서 가만 안 둘 거야"
    for d in detect(text):
        assert d.phrase == text[d.start : d.end]
        assert "\\s" not in d.phrase


def test_갈래마다_근거_조항이_다르다():
    """대응이 다르므로 근거 조항도 달라야 한다 — 화면이 무엇을 인용할지가 갈린다."""
    (insult,) = detect("이 씨발")
    (distress,) = detect("죽고 싶어요")
    assert insult.source_doc_id == "DASAN-MANUAL-5.1"
    assert distress.source_doc_id == "DASAN-MANUAL-5.4"


def test_같은_구간이_두_번_잡히지_않는다():
    for d_a, d_b in zip(detect("씨발 개새끼야 찾아간다"), detect("씨발 개새끼야 찾아간다")[1:]):
        assert d_a.end <= d_b.start
