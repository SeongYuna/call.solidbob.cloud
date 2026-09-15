# Requirement: J-5, QUA-1
"""배정 판정·설정 인터랙터 — 입력 정리만 하고 판정은 포트에 맡긴다."""

import asyncio

import pytest

from hub.app.dtos.blacklist_dto import RoutingDecision
from hub.app.dtos.routing_decision_dto import MAX_CANDIDATES, RoutedCall, RoutingDecisionCommand
from hub.app.dtos.routing_setting_dto import RoutingSetting, RoutingSettingCommand
from hub.app.ports.output.agent_routing_port import AgentRoutingPort
from hub.app.ports.output.routing_setting_port import RoutingSettingPort
from hub.app.use_cases.routing_decision_interactor import RoutingDecisionInteractor
from hub.app.use_cases.routing_setting_interactor import RoutingSettingInteractor


class _Routing(AgentRoutingPort):
    def __init__(self):
        self.calls = []

    async def route_call(self, call_id, candidate_ids):
        self.calls.append((call_id, candidate_ids))
        return RoutedCall(call_id=call_id, customer_identified=True, veteran_years=3.0,
                          decision=RoutingDecision(agent_id=None, is_blacklisted=False, fell_back=False, reason="x"))


class _Settings(RoutingSettingPort):
    def __init__(self):
        self.saved = []

    async def get(self):
        return RoutingSetting(veteran_years=3.0, saved=False)

    async def save(self, veteran_years, updated_by):
        self.saved.append((veteran_years, updated_by))
        return RoutingSetting(veteran_years=veteran_years, saved=True, updated_by=updated_by)


def test_후보는_공백을_빼고_중복을_합치되_순서를_지킨다():
    port = _Routing()
    asyncio.run(RoutingDecisionInteractor(port).decide(RoutingDecisionCommand(call_id="c1", candidate_ids=("a2", " ", "a1", "a2"))))
    assert port.calls == [("c1", ("a2", "a1"))]


def test_빈_call_id_와_너무_많은_후보는_거부한다():
    port = _Routing()
    with pytest.raises(ValueError):
        asyncio.run(RoutingDecisionInteractor(port).decide(RoutingDecisionCommand(call_id=" ", candidate_ids=())))
    with pytest.raises(ValueError):
        asyncio.run(RoutingDecisionInteractor(port).decide(RoutingDecisionCommand(
            call_id="c1", candidate_ids=tuple(f"a{i}" for i in range(MAX_CANDIDATES + 1)))))
    assert port.calls == []


@pytest.mark.parametrize("years,ok", [(0.5, True), (40, True), (0.4, False), (41, False)])
def test_근속_기준_범위(years, ok):
    port = _Settings()
    run = lambda: asyncio.run(RoutingSettingInteractor(port).save(RoutingSettingCommand(veteran_years=years, updated_by=1)))
    if ok:
        assert run().veteran_years == years
    else:
        with pytest.raises(ValueError):
            run()
        assert port.saved == []
