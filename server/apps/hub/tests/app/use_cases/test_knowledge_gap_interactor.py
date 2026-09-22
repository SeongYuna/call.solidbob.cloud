# Requirement: D-4, QUA-1
"""스텁 포트로 배선·검증만 본다."""

import asyncio

import pytest

from hub.app.dtos.knowledge_gap_dto import KnowledgeGapReport
from hub.app.ports.output import KnowledgeGapPort
from hub.app.use_cases.knowledge_gap_interactor import MAX_DESCRIPTION, KnowledgeGapInteractor


class _Spy(KnowledgeGapPort):
    def __init__(self):
        self.saved = []

    async def save(self, report):
        self.saved.append(report)
        return 4321


def _run(port, **kw):
    base = dict(module="B", description="반품 배송비 부담 주체를 못 찾음", call_id="c_001", segment_id=31)
    base.update(kw)
    return asyncio.run(KnowledgeGapInteractor(gaps=port).report(KnowledgeGapReport(**base)))


def test_신고를_그대로_저장한다():
    port = _Spy()
    receipt = _run(port)
    assert port.saved[0].module == "B"
    assert port.saved[0].call_id == "c_001"
    assert receipt.gap_id == 4321


@pytest.mark.parametrize("module", ["B", "C", "F"])
def test_세_갈래를_모두_받는다(module):
    """2.5절 D-4 확장 — B 검색 실패 · C 놓친 위반 · F 사후 문제."""
    port = _Spy()
    _run(port, module=module)
    assert port.saved[0].module == module


def test_설명_앞뒤_공백을_제거한다():
    port = _Spy()
    _run(port, description="  못 찾음  ")
    assert port.saved[0].description == "못 찾음"


def test_통화_연결_없이도_접수된다():
    """통화 밖에서 발견한 공백도 받는다 — 입구에서 거르지 않는다."""
    port = _Spy()
    _run(port, call_id=None, segment_id=None)
    assert port.saved[0].call_id is None


def test_중복이든_애매하든_거르지_않는다():
    """무엇이 공백인지 판단하는 것은 집계 단계(ai/) 몫이다."""
    port = _Spy()
    _run(port); _run(port)
    assert len(port.saved) == 2


@pytest.mark.parametrize("description", ["", "   "])
def test_빈_설명은_거부한다(description):
    port = _Spy()
    with pytest.raises(ValueError):
        _run(port, description=description)
    assert port.saved == []


def test_컬럼_길이를_넘으면_거부한다():
    """db description VARCHAR(300) — 넘겨서 잘리면 신고 내용이 소리 없이 사라진다."""
    port = _Spy()
    with pytest.raises(ValueError):
        _run(port, description="가" * (MAX_DESCRIPTION + 1))
    assert port.saved == []


def test_설명은_마스킹한_뒤_저장한다():
    """C-5·SEC-1 — 상담원이 자유롭게 쓰는 칸이라 번호가 들어올 수 있다. 전에는 마스킹 없이 저장됐다(미결 09-22)."""
    from hub.app.dtos import MaskedSpan  # noqa: PLC0415
    from hub.app.ports.output import MaskingPort  # noqa: PLC0415

    class _Digits(MaskingPort):
        def mask(self, text):
            return "".join("*" if ch.isdigit() else ch for ch in text), (MaskedSpan(type="P4", span=(0, 1)),)

    port = _Spy()
    asyncio.run(KnowledgeGapInteractor(gaps=port, masking=_Digits()).report(
        KnowledgeGapReport(module="B", description="고객 01012345678 번호로 문의한 서류")))
    assert port.saved[0].description == "고객 *********** 번호로 문의한 서류"
