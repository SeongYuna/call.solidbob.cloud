# Requirement: F-3, SEC-2
"""브리핑 조립. 기본 composer 는 **규칙 브리핑**(`server/apps/briefing`) — 모델은 `server/main.py` 의
`_wire_briefing_model` 이 `get_customer_briefing_port` 를 덮어써 얹는다. PostgreSQL 이 없으면 501."""

from __future__ import annotations

from datetime import datetime, timezone

from briefing.adapter.outbound.rule_briefing_adapter import RuleBriefingAdapter
from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.briefing_facts_repository import PostgresBriefingFactsRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.input.customer_briefing_use_case import CustomerBriefingUseCase
from hub.app.ports.output.briefing_facts_port import BriefingFactsPort
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort
from hub.app.use_cases.customer_briefing_interactor import BriefingCache, CustomerBriefingInteractor

_CACHE = BriefingCache()


def reset_briefing_cache() -> None:
    """테스트 전용 — 프로세스 단일 캐시를 비운다."""
    global _CACHE
    _CACHE = BriefingCache()


def get_briefing_facts_port(request: Request) -> BriefingFactsPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                            detail="PostgreSQL 이 설정되지 않았습니다 — infra/README.md 참고")
    return PostgresBriefingFactsRepository(build_connection_factory(settings))


def get_customer_briefing_port() -> CustomerBriefingPort:
    return RuleBriefingAdapter()


def get_customer_briefing_use_case(
    facts: BriefingFactsPort = Depends(get_briefing_facts_port),
    composer: CustomerBriefingPort = Depends(get_customer_briefing_port),
) -> CustomerBriefingUseCase:
    return CustomerBriefingInteractor(facts=facts, composer=composer, cache=_CACHE,
                                      now=lambda: datetime.now(timezone.utc))
