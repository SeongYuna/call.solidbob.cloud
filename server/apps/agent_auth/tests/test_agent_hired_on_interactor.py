# Requirement: J-5, QUA-1
"""입사일 저장 — 오늘보다 뒤는 받지 않는다(근속이 음수가 된다). 오늘은 받는다."""

import asyncio
from datetime import date

import pytest

from agent_auth.app.dtos.agent_directory_dto import AgentHiredOnCommand
from agent_auth.app.use_cases.agent_hired_on_interactor import AgentHiredOnInteractor

from ._fakes import FakeAgentDirectory

TODAY = date(2026, 9, 22)


def _set(port, hired_on):
    return asyncio.run(AgentHiredOnInteractor(port, today=lambda: TODAY).set(AgentHiredOnCommand("agent-1", hired_on)))


def test_오늘은_받는다():
    port = FakeAgentDirectory({"agent-1": "김민준"})
    assert _set(port, TODAY).hired_on == TODAY


def test_내일은_받지_않는다():
    port = FakeAgentDirectory({"agent-1": "김민준"})
    with pytest.raises(ValueError):
        _set(port, date(2026, 9, 23))
    assert "agent-1" not in port.hired


def test_없는_상담원은_None_이다():
    assert _set(FakeAgentDirectory(), TODAY) is None
