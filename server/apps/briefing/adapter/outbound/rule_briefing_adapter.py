# Requirement: F-3
from __future__ import annotations

from hub.app.dtos.customer_briefing_dto import BriefingComposition, BriefingFacts
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort

from ...domain.services.briefing_rules import rule_lines, rule_purpose


class RuleBriefingAdapter(CustomerBriefingPort):
    """규칙 브리핑. 모델 어댑터(`ai/apps/customer_briefing`)의 폴백이기도 하다."""

    async def compose(self, facts: BriefingFacts) -> BriefingComposition:
        return BriefingComposition(purpose=rule_purpose(facts), lines=rule_lines(facts))
