# Requirement: F-3
"""`CustomerBriefingPort` 모델 구현 — 규칙 브리핑 **위에** 목적 범주·세 줄을 얹는다(`decisions/220` 2절).

목적 **범주는 규칙이 정한다**(절대 원칙 9 — 판정은 규칙, 설명만 LLM). 모델은 규칙과 **같은 범주일 때만** 문장을 다시 쓴다
(`decisions/220` 결과 절, 2026-10-06 측정: 모델 범주 0/9 vs 규칙 2/3).

모델 실패 · 시간 초과(기본 10초) · JSON 아님 · 검사(`briefing_problems`) 하나라도 걸림 → **규칙 브리핑 그대로**.
`fallback`·`chat` 은 주입이다 — `server/apps/briefing`·`ai/apps/generation` 을 import 하지 않는다(계약 2).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Protocol

from hub.app.dtos.customer_briefing_dto import BriefingComposition, BriefingFacts, BriefingPurpose
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort

from ...domain.services.briefing_checks import OUTPUT_SCHEMA, briefing_problems, build_messages, render_facts

log = logging.getLogger(__name__)


class ChatClient(Protocol):
    model: str

    def chat(self, messages: list[dict[str, str]], *, schema: dict | None = None): ...


class ModelBriefingAdapter(CustomerBriefingPort):
    def __init__(self, fallback: CustomerBriefingPort, *, chat: ChatClient | None, timeout_s: float = 10.0) -> None:
        self._fallback = fallback
        self._chat = chat
        self._timeout = timeout_s

    async def compose(self, facts: BriefingFacts) -> BriefingComposition:
        rule = await self._fallback.compose(facts)
        if self._chat is None:
            return rule
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._chat.chat, build_messages(facts), schema=OUTPUT_SCHEMA), timeout=self._timeout)
            data = json.loads(result.content)
            category, purpose, lines = str(data["category"]), str(data["purpose"]), [str(x) for x in data["lines"]]
        except Exception as e:  # noqa: BLE001 — 어떤 실패든 규칙 브리핑으로
            log.warning("브리핑 모델 실패 → 규칙: %s", type(e).__name__)
            return rule
        problems = briefing_problems(category, purpose, lines, render_facts(facts))
        if problems:
            log.info("브리핑 모델 출력 검사 걸림 → 규칙: %s", problems)
            return rule
        if category != rule.purpose.category:
            log.info("브리핑 모델 범주가 규칙과 다름 → 규칙: model=%s rule=%s", category, rule.purpose.category)
            return rule
        return BriefingComposition(purpose=BriefingPurpose(category, purpose, "model"), lines=tuple(lines))
