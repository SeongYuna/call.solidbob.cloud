# Requirement: 7.3절 전사 이벤트
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.transcript_ingest_use_case import TranscriptIngestUseCase
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.transcript_ingest_record_port import TranscriptIngestRecordPort
from hub.app.use_cases.transcript_ingest_interactor import TranscriptIngestInteractor
from hub.dependencies.masking_provider import get_masking_port
from hub.dependencies.transcript_record_provider import get_transcript_record_port
from masking.adapter.outbound.interim_masking_adapter import InterimMaskingAdapter


def get_transcript_ingest_use_case(
    masking: MaskingPort = Depends(get_masking_port),
    record: TranscriptIngestRecordPort = Depends(get_transcript_record_port),
) -> TranscriptIngestUseCase:
    # 중간 자막은 같은 마스킹 위에 숫자 덩어리 가드를 얹는다(C-5, 09-22) — NER 이 꽂혀도 그 위에 얹힌다
    return TranscriptIngestInteractor(masking=masking, record=record, interim_masking=InterimMaskingAdapter(masking))
