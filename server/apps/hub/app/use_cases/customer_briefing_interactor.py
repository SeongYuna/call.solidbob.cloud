# Requirement: F-3
"""브리핑 인터랙터 — 사실을 받아 상태를 가르고, 지난 통화가 있을 때만 composer 를 부른다. **목적을 정하지 않는다**(포트 몫).

같은 통화는 한 번만 만든다 — 화면이 `started` 를 다시 받거나 재렌더해도 모델이 두 번 돌지 않게(`BriefingCache`).
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime
from typing import Awaitable, Callable

from hub.app.dtos.customer_briefing_dto import BriefingCallNotFound, CustomerBriefing
from hub.app.ports.input.customer_briefing_use_case import CustomerBriefingUseCase
from hub.app.ports.output.briefing_facts_port import BriefingFactsPort
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort


class BriefingCache:
    def __init__(self, max_items: int = 256) -> None:
        self._max = max_items
        self._done: OrderedDict[str, CustomerBriefing] = OrderedDict()
        self._inflight: dict[str, asyncio.Future] = {}

    async def get_or_create(self, call_id: str, factory: Callable[[], Awaitable[CustomerBriefing]]) -> CustomerBriefing:
        while True:
            if call_id in self._done:
                self._done.move_to_end(call_id)
                return self._done[call_id]
            inflight = self._inflight.get(call_id)
            if inflight is None:
                break
            try:
                # shield — 기다리는 쪽이 취소돼도(클라이언트 끊김) 공유 future 는 취소되지 않는다
                return await asyncio.shield(inflight)
            except asyncio.CancelledError:
                task = asyncio.current_task()
                if inflight.cancelled() and not (task is not None and task.cancelling()):
                    continue  # 만든 쪽이 취소됐다 — 내가 새로 만든다
                raise
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._inflight[call_id] = fut
        try:
            result = await factory()
        except asyncio.CancelledError:
            fut.cancel()  # 기다리는 쪽에 취소 예외를 「자기 취소」처럼 넘기지 않고 재시도하게 한다
            raise
        except Exception as exc:
            if not fut.done():
                fut.set_exception(exc)
                fut.exception()  # 기다리는 쪽이 없어도 「처리 안 된 예외」 경고가 나지 않게
            raise
        finally:
            if self._inflight.get(call_id) is fut:
                del self._inflight[call_id]
        if not fut.done():
            fut.set_result(result)
        self._done[call_id] = result
        if len(self._done) > self._max:
            self._done.popitem(last=False)
        return result


class CustomerBriefingInteractor(CustomerBriefingUseCase):
    def __init__(self, facts: BriefingFactsPort, composer: CustomerBriefingPort, cache: BriefingCache,
                 now: Callable[[], datetime]) -> None:
        self._facts = facts
        self._composer = composer
        self._cache = cache
        self._now = now

    async def get(self, call_id: str) -> CustomerBriefing:
        if not call_id.strip():
            raise ValueError("call_id 가 비어 있습니다")
        return await self._cache.get_or_create(call_id, lambda: self._build(call_id))

    async def _build(self, call_id: str) -> CustomerBriefing:
        facts = await self._facts.collect(call_id)
        if facts is None:
            raise BriefingCallNotFound(f"통화가 없습니다: {call_id}")
        prior = facts.prior_calls
        common = dict(call_id=call_id, prior_call_count=len(prior), evidence=prior,
                      open_follow_ups=sum(len(p.open_follow_ups) for p in prior),
                      call_guard_categories=tuple(sorted({c for p in prior for c in p.call_guard_categories})),
                      blacklisted=facts.blacklisted, generated_at=self._now())
        if not facts.customer_identified:
            return CustomerBriefing(status="unidentified", purpose=None, lines=(), **common)
        if not prior:
            return CustomerBriefing(status="first_contact", purpose=None, lines=(), **common)
        comp = await self._composer.compose(facts)
        return CustomerBriefing(status="ready", purpose=comp.purpose, lines=comp.lines, **common)
