# Requirement: J-4, QUA-1
"""관리자 ↔ `agent` 행 연결(`decisions/314`) — 있으면 그대로 · 없으면 `admin-<id>` 로 붙인다 ·
이름이 같은 상담원이 있어도 그 행을 빌리지 않는다 · 먼저 쓴 연결이 이긴다."""

import asyncio

from admin_auth.app.dtos.admin_identity_dto import AdminAccount
from admin_auth.app.ports.output.admin_account_port import AdminAccountPort
from agent_auth.app.use_cases.admin_agent_link_interactor import AdminAgentLinkInteractor

from ._fakes import FakeAgentDirectory


class _Admins(AdminAccountPort):
    def __init__(self, linked: dict[int, str] | None = None) -> None:
        self.linked = dict(linked or {})

    async def find_by_email(self, email):
        raise NotImplementedError

    async def find_by_id(self, account_id):
        raise NotImplementedError

    async def link_agent(self, account_id: int, agent_id: str) -> str:
        return self.linked.setdefault(account_id, agent_id)  # 실제 구현의 COALESCE 와 같다


def _resolve(admin, agents=None, admins=None):
    agents = agents if agents is not None else FakeAgentDirectory()
    admins = admins if admins is not None else _Admins()
    return asyncio.run(AdminAgentLinkInteractor(agents, admins).resolve(admin)), agents, admins


def test_이미_연결된_관리자는_그_ID_그대로다_아무것도_만들지_않는다():
    got, agents, admins = _resolve(AdminAccount(id=1, email="a@x", name="가", agent_id="kim-agent"))
    assert got == "kim-agent"
    assert agents.admin_rows == {} and admins.linked == {}


def test_연결이_없으면_admin_id_행을_만들어_잇는다():
    got, agents, admins = _resolve(AdminAccount(id=7, email="a@x", name="장민석"))
    assert got == "admin-7"
    assert agents.admin_rows == {"admin-7": "장민석"}
    assert admins.linked == {7: "admin-7"}


def test_이름이_같은_상담원이_있어도_그_행을_빌리지_않는다():
    agents = FakeAgentDirectory({"장민석": "장민석"})
    got, agents, _ = _resolve(AdminAccount(id=7, email="a@x", name="장민석"), agents=agents)
    assert got == "admin-7"
    assert agents.agents == {"장민석": "장민석"}  # 상담원 행은 그대로


def test_이름이_없으면_이메일이_아니라_ID를_이름으로_쓴다():
    _, agents, _ = _resolve(AdminAccount(id=3, email="secret@example.com", name=None))
    assert agents.admin_rows == {"admin-3": "admin-3"}


def test_이름은_30자로_자른다():
    _, agents, _ = _resolve(AdminAccount(id=3, email="a@x", name="가" * 40))
    assert len(agents.admin_rows["admin-3"]) == 30


def test_동시에_다른_값이_먼저_연결됐으면_그_값을_돌려준다():
    got, _, _ = _resolve(AdminAccount(id=7, email="a@x", name="가"), admins=_Admins({7: "earlier"}))
    assert got == "earlier"
