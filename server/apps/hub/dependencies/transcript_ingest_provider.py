# Requirement: 7.3절 전사 이벤트
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.transcript_ingest_use_case import TranscriptIngestUseCase
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.transcript_ingest_record_port import TranscriptIngestRecordPort
from hub.app.use_cases.transcript_ingest_interactor import TranscriptIngestInteractor
from hub.dependencies.masking_provider import get_masking_port
from hub.dependencies.transcript_record_provider import get_transcript_record_port


def get_transcript_ingest_use_case(
    masking: MaskingPort = Depends(get_masking_port),
    record: TranscriptIngestRecordPort = Depends(get_transcript_record_port),
) -> TranscriptIngestUseCase:
    return TranscriptIngestInteractor(masking=masking, record=record)
