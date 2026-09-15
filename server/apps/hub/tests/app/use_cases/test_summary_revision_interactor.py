# Requirement: D-1, D-2, D-3, SEC-1, QUA-1
"""요약 재수정: 사유 필수 · 사람이 쓴 문구 전부 마스킹 · 잘못된 입력은 포트를 부르지 않는다."""

import asyncio
from datetime import datetime, timezone

import pytest

from hub.app.dtos.summary_revision_dto import SummaryRevision, SummaryRevisionCommand
from hub.app.ports.output.summary_revision_port import SummaryRevisionPort
from hub.app.use_cases.summary_revision_interactor import SummaryRevisionInteractor

from ._blacklist_stubs import DigitMasking

AT = datetime(2026, 9, 15, 5, 0, tzinfo=timezone.utc)


class _Port(SummaryRevisionPort):
    def __init__(self):
        self.calls = []

    async def revise(self, call_id, *, summary_text, inquiry_type, follow_up_actions, reason):
        self.calls.append((call_id, summary_text, inquiry_type, follow_up_actions, reason))
        return SummaryRevision(revision_id=1, call_id=call_id, previous_summary_text="이전", previous_inquiry_type=None,
                               reason=reason, revised_at=AT)

    async def list_revisions(self, call_id):
        return []


def _run(port, **kw):
    cmd = dict(call_id="c1", summary_text="고친 요약 010-1111-2222", reason="번호 오기 010-1111-2222",
               inquiry_type="전입신고", follow_up_actions=("회신 010-1111-2222",))
    cmd.update(kw)
    return asyncio.run(SummaryRevisionInteractor(port, DigitMasking()).revise(SummaryRevisionCommand(**cmd)))


def test_사유와_문구를_전부_마스킹해_넘긴다():
    port = _Port()
    revised = _run(port)
    assert port.calls == [("c1", "고친 요약 ***-****-****", "전입신고", ("회신 ***-****-****",), "번호 오기 ***-****-****")]
    assert revised.revision.reason == "번호 오기 ***-****-****"


@pytest.mark.parametrize("kw", [{"reason": "  "}, {"summary_text": ""}, {"inquiry_type": "가" * 31},
                                {"follow_up_actions": tuple(str(i) for i in range(21))}])
def test_잘못된_입력은_포트를_부르지_않는다(kw):
    port = _Port()
    with pytest.raises(ValueError):
        _run(port, **kw)
    assert port.calls == []
