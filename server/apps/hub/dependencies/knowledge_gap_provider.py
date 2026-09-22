# Requirement: D-4, SEC-2
"""KnowledgeGapPort 프로바이더. PostgreSQL 이 없으면 501 — 신고를 받아놓고 버리지 않는다.

접수했다고 응답한 뒤 아무 데도 안 남으면, 상담원은 신고했다고 믿고 우리는 데이터가 없다.
그게 D-4 를 만든 목적과 정반대다.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.knowledge_gap_repository import PostgresKnowledgeGapRepository
from hub.app.ports.input.knowledge_gap_use_case import KnowledgeGapUseCase
from hub.app.ports.output.knowledge_gap_port import KnowledgeGapPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.use_cases.knowledge_gap_interactor import KnowledgeGapInteractor
from hub.dependencies.masking_provider import get_masking_port


def get_knowledge_gap_port(request: Request) -> KnowledgeGapPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PostgreSQL 이 설정되지 않았습니다 — 신고를 저장할 곳이 없습니다 (infra/README.md)",
        )
    return PostgresKnowledgeGapRepository(build_connection_factory(settings))


def get_knowledge_gap_use_case(
    gaps: KnowledgeGapPort = Depends(get_knowledge_gap_port),
    masking: MaskingPort = Depends(get_masking_port),
) -> KnowledgeGapUseCase:
    return KnowledgeGapInteractor(gaps=gaps, masking=masking)
