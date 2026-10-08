# Requirement: 7.3절 전사 이벤트, SEC-1, SEC-2
"""TranscriptIngestRecordPort 프로바이더 — PostgreSQL 설정이 있으면 리포지토리, 없으면 로그 어댑터.

로그 어댑터를 지우지 않은 이유: DB 없이 도는 경로가 있어야 로컬·CI 에서 파이프라인을 확인할 수 있다.
**둘 다 마스킹 후 이벤트만 받으므로** 어느 쪽으로 떨어져도 SEC-1 은 깨지지 않는다.
"""

from __future__ import annotations

from fastapi import Request

from hub.adapter.outbound.log_transcript_ingest_record_adapter import LogTranscriptIngestRecordAdapter
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.adapter.outbound.postgres.transcript_segment_repository import PostgresTranscriptSegmentRepository
from hub.app.ports.output.transcript_ingest_record_port import TranscriptIngestRecordPort
from hub.dependencies.transcript_cipher_provider import transcript_cipher_of


def get_transcript_record_port(request: Request) -> TranscriptIngestRecordPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        return LogTranscriptIngestRecordAdapter()
    return PostgresTranscriptSegmentRepository(
        build_connection_factory(settings), cipher=transcript_cipher_of(settings)
    )
