# Requirement: A-1, SEC-1, SEC-2
"""TranscriptQueryPort 프로바이더. **PostgreSQL 설정이 없으면 501** 이다.

기록 포트와 달리 로그 폴백이 없다 — 로그에는 조회할 것이 없기 때문이다.
빈 목록을 돌려주면 "이 통화에 발화가 없음"으로 읽혀 DB 미설정과 구분되지 않는다.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.transcript_query_repository import PostgresTranscriptQueryRepository
from hub.app.ports.input.transcript_query_use_case import TranscriptQueryUseCase
from hub.app.ports.output.transcript_query_port import TranscriptQueryPort
from hub.app.use_cases.transcript_query_interactor import TranscriptQueryInteractor
from hub.dependencies.transcript_cipher_provider import transcript_cipher_of


def get_transcript_query_port(request: Request) -> TranscriptQueryPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PostgreSQL 이 설정되지 않았습니다 — infra/README.md 참고",
        )
    return PostgresTranscriptQueryRepository(build_connection_factory(settings), cipher=transcript_cipher_of(settings))


def get_transcript_query_use_case(
    query_port: TranscriptQueryPort = Depends(get_transcript_query_port),
) -> TranscriptQueryUseCase:
    return TranscriptQueryInteractor(query_port=query_port)
