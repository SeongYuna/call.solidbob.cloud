# Requirement: D-1, D-2, D-3, SEC-2
"""SummaryConfirmationPort 프로바이더. **PostgreSQL 설정이 없으면 501** — 확정은 저장이 전부라 로그로 대신하면 «확정됐다» 는 거짓말이 된다."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.summary_confirmation_repository import PostgresSummaryConfirmationRepository
from hub.app.ports.input.summary_confirmation_use_case import SummaryConfirmationUseCase
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.summary_confirmation_port import SummaryConfirmationPort
from hub.app.use_cases.summary_confirmation_interactor import SummaryConfirmationInteractor
from hub.dependencies.masking_provider import get_masking_port


def get_summary_confirmation_port(request: Request) -> SummaryConfirmationPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PostgreSQL 이 설정되지 않았습니다 — 확정을 저장할 곳이 없습니다",
        )
    return PostgresSummaryConfirmationRepository(build_connection_factory(settings))


def get_summary_confirmation_use_case(
    confirmation: SummaryConfirmationPort = Depends(get_summary_confirmation_port),
    masking: MaskingPort = Depends(get_masking_port),
) -> SummaryConfirmationUseCase:
    return SummaryConfirmationInteractor(confirmation=confirmation, masking=masking)
