# Requirement: F-2, QUA-1
"""안내 여부 자동 판정 — 키워드 규칙. 한계(부정 문맥)도 테스트로 고정해 둔다 — 고친 척하지 않는다."""

from closure_gate.domain.services.detection import informed_documents
from closure_gate.domain.value_objects.closure_rule import RULES

INITIAL = RULES["DASAN-TERM-4.4"]  # 전입신고: 신고서 · 신고인 신분증


def test_안내한_서류만_참이다():
    got = informed_documents(INITIAL, ["네 전입신고는 신고서 작성하시면 됩니다"])
    assert got == {"신고서": True, "신고인 신분증": False}


def test_신분증은_1_4조의_인정_서류_이름으로도_센다_공백도_무시한다():
    got = informed_documents(INITIAL, ["신고서랑", "운전 면허증 가져오세요"])
    assert got == {"신고서": True, "신고인 신분증": True}


def test_발화가_없으면_전부_안내하지_않은_것이다():
    assert set(informed_documents(INITIAL, []).values()) == {False}


def test_한계_부정_문맥도_안내로_센다():
    """「필요 없어요」 도 안내로 센다 — 누락을 못 잡는 쪽의 오류다. 골든셋으로 재야 할 한계(측정 불가 상태)."""
    got = informed_documents(INITIAL, ["신고서는 필요 없어요"])
    assert got["신고서"] is True
