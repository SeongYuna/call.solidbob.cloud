# Requirement: C-6, QUA-1
import asyncio

import pytest

from hub.app.dtos.call_guard_flag_list_dto import CallGuardFlagListQuery
from hub.app.ports.output.call_guard_flag_query_port import CallGuardFlagQueryPort
from hub.app.use_cases.call_guard_flag_list_interactor import CallGuardFlagListInteractor


class _Port(CallGuardFlagQueryPort):
    def __init__(self):
        self.calls = []

    async def list_flags(self, call_id, category, limit, offset):
        self.calls.append(("list", call_id, category, limit, offset))
        return []

    async def count_flags(self, call_id, category):
        self.calls.append(("count", call_id, category))
        return 4


def test_필터를_목록과_총수에_같이_넘긴다():
    port = _Port()
    page = asyncio.run(CallGuardFlagListInteractor(port).list(CallGuardFlagListQuery(call_id="c1", category="distress", limit=10)))
    assert page.total == 4
    assert port.calls == [("list", "c1", "distress", 10, 0), ("count", "c1", "distress")]


@pytest.mark.parametrize("kw", [{"category": "폭언"}, {"limit": 0}, {"offset": -1}])
def test_갈래_이름이나_경계가_틀리면_거부한다(kw):
    port = _Port()
    with pytest.raises(ValueError):
        asyncio.run(CallGuardFlagListInteractor(port).list(CallGuardFlagListQuery(**kw)))
    assert port.calls == []
