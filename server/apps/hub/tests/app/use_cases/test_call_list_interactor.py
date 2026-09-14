# Requirement: D-1, D-2, QUA-1
"""스텁 포트로 페이지 경계·필터 전달만 본다."""

import asyncio
from datetime import datetime, timezone

import pytest

from hub.app.dtos.call_list_dto import MAX_LIMIT, CallListItem, CallListQuery
from hub.app.ports.output.call_list_port import CallListPort
from hub.app.use_cases.call_list_interactor import CallListInteractor

ITEM = CallListItem(
    call_id="test-1", domain="dasan", started_at=datetime(2026, 9, 14, 1, 2, tzinfo=timezone.utc), ended_at=None,
    status="in_progress", stt_engine="google-stt", channel_count=2, customer_id=None, inquiry_type=None,
    summary_confirmed=False,
)


class _Port(CallListPort):
    def __init__(self):
        self.calls = []

    async def list_calls(self, limit, offset, customer_id):
        self.calls.append(("list", limit, offset, customer_id))
        return [ITEM]

    async def count_calls(self, customer_id):
        self.calls.append(("count", customer_id))
        return 31


def _run(port, **kw):
    return asyncio.run(CallListInteractor(list_port=port).list(CallListQuery(**kw)))


def test_페이지와_총수를_돌려준다():
    port = _Port()
    page = _run(port, limit=10, offset=20)
    assert page.calls == (ITEM,) and page.total == 31 and (page.limit, page.offset) == (10, 20)
    assert port.calls == [("list", 10, 20, None), ("count", None)]


def test_고객_필터를_목록과_총수에_같이_넘긴다():
    port = _Port()
    _run(port, customer_id=" cust-9 ")
    assert port.calls == [("list", 50, 0, "cust-9"), ("count", "cust-9")]


@pytest.mark.parametrize("kw", [{"limit": 0}, {"limit": MAX_LIMIT + 1}, {"offset": -1}, {"customer_id": "  "}])
def test_경계를_벗어나면_거부한다(kw):
    port = _Port()
    with pytest.raises(ValueError):
        _run(port, **kw)
    assert port.calls == []
