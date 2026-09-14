# Requirement: J-2, J-4, SEC-2
"""BlacklistPort · BlacklistEvidencePort 프로바이더. **PostgreSQL 이 없으면 501** — 요청을 받아 놓고 버리지 않는다."""

from __future__ import annotations

from blacklist.adapter.outbound.postgres_blacklist_repository import PostgresBlacklistRepository
from fastapi import HTTPException, Request, status

from hub.adapter.outbound.postgres.blacklist_evidence_repository import PostgresBlacklistEvidenceRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.output.blacklist_evidence_port import BlacklistEvidencePort
from hub.app.ports.output.blacklist_port import BlacklistPort


def _connect(request: Request):
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PostgreSQL 이 설정되지 않았습니다 — 블랙리스트 요청을 저장할 곳이 없습니다",
        )
    return build_connection_factory(settings)


def get_blacklist_port(request: Request) -> BlacklistPort:
    return PostgresBlacklistRepository(_connect(request))


def get_blacklist_evidence_port(request: Request) -> BlacklistEvidencePort:
    return PostgresBlacklistEvidenceRepository(_connect(request))
