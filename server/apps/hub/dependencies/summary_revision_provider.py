# Requirement: D-1, D-2, D-3, SEC-2
"""SummaryRevisionPort 프로바이더. **PostgreSQL 설정이 없으면 501** — 이력이 저장이 전부다."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.summary_revision_repository import PostgresSummaryRevisionRepository
from hub.app.ports.input.summary_revision_list_use_case import SummaryRevisionListUseCase
from hub.app.ports.input.summary_revision_use_case import SummaryRevisionUseCase
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.summary_revision_port import SummaryRevisionPort
from hub.app.use_cases.summary_revision_interactor import SummaryRevisionInteractor
from hub.app.use_cases.summary_revision_list_interactor import SummaryRevisionListInteractor
from hub.dependencies.masking_provider import get_masking_port


def get_summary_revision_port(request: Request) -> SummaryRevisionPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PostgreSQL 이 설정되지 않았습니다 — 요약 수정 이력을 저장할 곳이 없습니다",
        )
    return PostgresSummaryRevisionRepository(build_connection_factory(settings))


def get_summary_revision_use_case(
    revisions: SummaryRevisionPort = Depends(get_summary_revision_port),
    masking: MaskingPort = Depends(get_masking_port),
) -> SummaryRevisionUseCase:
    return SummaryRevisionInteractor(revisions=revisions, masking=masking)


def get_summary_revision_list_use_case(
    revisions: SummaryRevisionPort = Depends(get_summary_revision_port),
) -> SummaryRevisionListUseCase:
    return SummaryRevisionListInteractor(revisions=revisions)
