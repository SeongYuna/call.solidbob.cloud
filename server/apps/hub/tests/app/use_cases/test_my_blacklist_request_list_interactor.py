# Requirement: J-2, J-4, QUA-1
import asyncio

from hub.app.use_cases.my_blacklist_request_list_interactor import MyBlacklistRequestListInteractor

from ._blacklist_stubs import StubBlacklist


def test_요청자로만_거른다_상태는_거르지_않는다():
    port = StubBlacklist()
    asyncio.run(MyBlacklistRequestListInteractor(port).list("a_01"))
    assert port.calls == [("list_requests", None, "a_01")]
