# Requirement: D-1, D-2, D-3, SEC-1, QUA-1
"""요약 확정: 상담원이 쓴 문구를 마스킹해 넘긴다 · 빈 요약·과한 입력은 포트를 부르지 않고 거부."""

import asyncio
from datetime import datetime, timezone

import pytest

from hub.app.dtos.summary_confirmation_dto import MAX_FOLLOW_UPS, SummaryConfirmationCommand
from hub.app.ports.output.summary_confirmation_port import SummaryConfirmationPort
from hub.app.use_cases.summary_confirmation_interactor import SummaryConfirmationInteractor

from ._blacklist_stubs import DigitMasking

AT = datetime(2026, 9, 15, 4, 0, tzinfo=timezone.utc)


class _Port(SummaryConfirmationPort):
    def __init__(self):
        self.calls = []

    async def confirm(self, call_id, *, summary_text, inquiry_type, follow_up_actions):
        self.calls.append((call_id, summary_text, inquiry_type, follow_up_actions))
        return AT


def _run(port, **kw):
    cmd = dict(call_id="c1", summary_text="전입신고 서류 문의 — 010-1234-5678 로 회신", inquiry_type="전입신고",
               follow_up_actions=("문자 발송 010-1234-5678", "  "))
    cmd.update(kw)
    return asyncio.run(SummaryConfirmationInteractor(port, DigitMasking()).confirm(SummaryConfirmationCommand(**cmd)))


def test_상담원이_쓴_문구를_마스킹해_확정한다():
    port = _Port()
    confirmed = _run(port)
    assert port.calls == [("c1", "전입신고 서류 문의 — ***-****-**** 로 회신", "전입신고", ("문자 발송 ***-****-****",))]
    assert confirmed.confirmed_at == AT and confirmed.follow_up_actions == ("문자 발송 ***-****-****",)  # 빈 항목은 뺀다


def test_유형은_비워도_된다():
    port = _Port()
    _run(port, inquiry_type="   ")
    assert port.calls[0][2] is None


@pytest.mark.parametrize("kw", [
    {"summary_text": "  "},
    {"inquiry_type": "가" * 31},
    {"follow_up_actions": tuple(f"조치 {i}" for i in range(MAX_FOLLOW_UPS + 1))},
])
def test_잘못된_입력은_포트를_부르지_않고_거부한다(kw):
    port = _Port()
    with pytest.raises(ValueError):
        _run(port, **kw)
    assert port.calls == []
