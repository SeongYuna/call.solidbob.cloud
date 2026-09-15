# Requirement: J-1, SEC-1, QUA-1
"""발급은 해시만 저장하고 원문을 한 번 돌려준다 · 폐기된 토큰과 형식이 다른 값은 상담원이 아니다."""

import asyncio

import pytest

from agent_auth.app.dtos.agent_token_dto import AgentTokenNotFound, IssueAgentTokenCommand, UnknownAgentError
from agent_auth.app.use_cases.agent_token_list_interactor import AgentTokenListInteractor
from agent_auth.app.use_cases.current_agent_interactor import CurrentAgentInteractor
from agent_auth.app.use_cases.issue_agent_token_interactor import IssueAgentTokenInteractor
from agent_auth.app.use_cases.revoke_agent_token_interactor import RevokeAgentTokenInteractor
from agent_auth.domain.services.agent_token import TOKEN_PREFIX, hash_token, new_token

from ._fakes import FakeAgentTokens


def _issue(port, agent_id="agent-7"):
    return asyncio.run(IssueAgentTokenInteractor(port).issue(IssueAgentTokenCommand(agent_id=agent_id, issued_by=3)))


def test_토큰은_접두어가_붙은_난수이고_매번_다르다():
    a, b = new_token(), new_token()
    assert a.startswith(TOKEN_PREFIX) and a != b and len(a) > 40


def test_발급은_해시만_저장하고_원문을_한_번_돌려준다():
    port = FakeAgentTokens()
    issued = _issue(port)
    (row,) = port.rows
    assert row["token_hash"] == hash_token(issued.token)
    assert issued.token not in str(port.rows)  # 원문은 저장소 어디에도 없다
    assert issued.item.agent_id == "agent-7" and issued.item.issued_by == 3


def test_없는_상담원에게는_발급하지_않는다():
    with pytest.raises(UnknownAgentError):
        _issue(FakeAgentTokens(), agent_id="nobody")


def test_빈_상담원_ID는_거절한다():
    with pytest.raises(ValueError):
        _issue(FakeAgentTokens(), agent_id="  ")


def test_발급한_토큰으로_상담원을_찾는다():
    port = FakeAgentTokens()
    issued = _issue(port)
    assert asyncio.run(CurrentAgentInteractor(port).current(issued.token)) == "agent-7"


def test_폐기한_토큰은_상담원이_아니다():
    port = FakeAgentTokens()
    issued = _issue(port)
    asyncio.run(RevokeAgentTokenInteractor(port).revoke(issued.item.id))
    assert asyncio.run(CurrentAgentInteractor(port).current(issued.token)) is None


def test_접두어가_다른_값은_조회하지_않고_거절한다():
    class _Boom(FakeAgentTokens):
        async def find_active_agent_id(self, token_hash):
            raise AssertionError("조회하면 안 된다")

    assert asyncio.run(CurrentAgentInteractor(_Boom()).current("eyJhbGciOi.jwt.like")) is None


def test_폐기는_멱등이고_없는_id는_404감이다():
    port = FakeAgentTokens()
    issued = _issue(port)
    first = asyncio.run(RevokeAgentTokenInteractor(port).revoke(issued.item.id))
    second = asyncio.run(RevokeAgentTokenInteractor(port).revoke(issued.item.id))
    assert first.revoked_at == second.revoked_at is not None
    with pytest.raises(AgentTokenNotFound):
        asyncio.run(RevokeAgentTokenInteractor(port).revoke(999))


def test_목록은_상담원으로_거를_수_있다():
    port = FakeAgentTokens(agents=("a1", "a2"))
    _issue(port, "a1")
    _issue(port, "a2")
    assert [t.agent_id for t in asyncio.run(AgentTokenListInteractor(port).list("a2"))] == ["a2"]
    assert len(asyncio.run(AgentTokenListInteractor(port).list(None))) == 2
