# Requirement: J-4, SEC-1, QUA-1
import asyncio
from datetime import timedelta

import pytest

from hub.app.dtos.blacklist_decision_dto import BlacklistDecisionCommand
from hub.app.use_cases.blacklist_decision_interactor import BlacklistDecisionInteractor

from ._blacklist_stubs import NOW, DigitMasking, StubBlacklist


def _run(**kw):
    blacklist = StubBlacklist()
    cmd = BlacklistDecisionCommand(**{"request_id": "7", "approve": True, "decided_by": "admin-1", **kw})
    asyncio.run(BlacklistDecisionInteractor(blacklist, DigitMasking(), now=lambda: NOW).decide(cmd))
    return blacklist.calls


def test_승인은_만료_일수를_시각으로_바꾸고_메모를_마스킹한다():
    calls = _run(expires_in_days=30, note="재통화 010-1111-2222 확인")
    assert calls == [("decide", "7", True, "admin-1", NOW + timedelta(days=30), "재통화 ***-****-**** 확인")]


@pytest.mark.parametrize("days", [None, 0, 366])
def test_승인에_만료_일수가_없거나_범위_밖이면_거부한다(days):
    """기본값을 두지 않는다 — 근거 없는 기간을 지어내지 않는다(`decisions/304`)."""
    with pytest.raises(ValueError):
        _run(expires_in_days=days)


def test_반려는_만료를_넘기지_않고_사유를_마스킹해_넘긴다():
    """`decisions/316` — 전엔 반려 메모를 버렸다. 이제 사유가 요청 행(`decision_note`)에 남는다."""
    calls = _run(approve=False, expires_in_days=30, note="010-1111-2222 로 재확인 결과 오인")
    assert calls == [("decide", "7", False, "admin-1", None, "***-****-**** 로 재확인 결과 오인")]


@pytest.mark.parametrize("note", [None, "", "   "])
def test_반려에_사유가_없으면_거부한다(note):
    with pytest.raises(ValueError, match="반려에는 사유"):
        _run(approve=False, note=note)


def test_승인_메모는_여전히_선택이다():
    assert _run(expires_in_days=30)[0][-1] is None
