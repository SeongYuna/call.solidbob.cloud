# Requirement: F-3
import asyncio
from datetime import datetime, timezone

import pytest

from hub.app.dtos.customer_briefing_dto import (
    BriefingCallNotFound, BriefingComposition, BriefingFacts, BriefingPurpose, PriorCall,
)
from hub.app.ports.output.briefing_facts_port import BriefingFactsPort
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort
from hub.app.use_cases.customer_briefing_interactor import BriefingCache, CustomerBriefingInteractor

T = datetime(2026, 10, 6, 5, 0, tzinfo=timezone.utc)
PRIOR = PriorCall(call_id="p1", started_at=T, inquiry_type="일반행정", summary_text="요약", summary_confirmed=True,
                  open_follow_ups=("회신",), call_guard_categories=("insult",))


class _Facts(BriefingFactsPort):
    def __init__(self, facts):
        self.facts = facts

    async def collect(self, call_id):
        return self.facts


class _Composer(CustomerBriefingPort):
    def __init__(self):
        self.calls = 0

    async def compose(self, facts):
        self.calls += 1
        await asyncio.sleep(0.01)
        return BriefingComposition(BriefingPurpose("후속 확인", "확인 전화로 보입니다", "model"), ("줄1",))


def _it(facts, composer=None):
    return CustomerBriefingInteractor(_Facts(facts), composer or _Composer(), BriefingCache(), now=lambda: T)


def test_not_found():
    with pytest.raises(BriefingCallNotFound):
        asyncio.run(_it(None).get("x"))


def test_empty_id_is_value_error():
    with pytest.raises(ValueError):
        asyncio.run(_it(None).get("  "))


def test_unidentified_does_not_compose():
    c = _Composer()
    b = asyncio.run(_it(BriefingFacts("now", customer_identified=False), c).get("now"))
    assert b.status == "unidentified" and b.purpose is None and c.calls == 0


def test_first_contact_does_not_compose():
    c = _Composer()
    b = asyncio.run(_it(BriefingFacts("now", customer_identified=True), c).get("now"))
    assert b.status == "first_contact" and b.prior_call_count == 0 and c.calls == 0


def test_ready_carries_signals():
    b = asyncio.run(_it(BriefingFacts("now", True, (PRIOR,), blacklisted=True)).get("now"))
    assert b.status == "ready" and b.prior_call_count == 1 and b.open_follow_ups == 1
    assert b.call_guard_categories == ("insult",) and b.blacklisted and b.purpose.category == "후속 확인"


def test_concurrent_requests_compose_once():
    c = _Composer()
    it = _it(BriefingFacts("now", True, (PRIOR,)), c)

    async def go():
        return await asyncio.gather(it.get("now"), it.get("now"))

    a, b = asyncio.run(go())
    assert c.calls == 1 and a == b
