# Requirement: B-5, E-1, SEC-2
"""RecommendationRecordPort 프로바이더 — PostgreSQL 이 있으면 리포지토리, 없으면 로그(card_id 는 null). 전사 기록과 같은 조건이다."""

from __future__ import annotations

from fastapi import Request

from hub.adapter.outbound.log_recommendation_record_adapter import LogRecommendationRecordAdapter
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.recommendation_repository import PostgresRecommendationRepository
from hub.app.ports.output.recommendation_record_port import RecommendationRecordPort


def get_recommendation_record_port(request: Request) -> RecommendationRecordPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        return LogRecommendationRecordAdapter()
    return PostgresRecommendationRepository(build_connection_factory(settings))
