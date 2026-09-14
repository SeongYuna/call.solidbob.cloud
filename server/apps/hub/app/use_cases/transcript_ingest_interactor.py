# Requirement: 7.3절 전사 이벤트, C-5, SEC-1
"""전사 수신 인터랙터 — 파이프라인의 입구. 원문이 살아 있는 구간은 이 함수의 첫 두 줄뿐이다."""

from __future__ import annotations

from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.dtos.transcript_ingest_dto import TranscriptIngestCommand
from hub.app.ports.input.transcript_ingest_use_case import TranscriptIngestUseCase
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.transcript_ingest_record_port import TranscriptIngestRecordPort


class TranscriptIngestInteractor(TranscriptIngestUseCase):
    def __init__(self, masking: MaskingPort, record: TranscriptIngestRecordPort) -> None:
        self._masking = masking
        self._record = record

    async def ingest(self, command: TranscriptIngestCommand) -> TranscriptEvent:
        masked_text, spans = self._masking.mask(command.raw_text)
        event = TranscriptEvent(
            call_id=command.call_id,
            segment_id=command.segment_id,
            speaker=command.speaker,
            text=masked_text,
            is_final=command.is_final,
            utterance_end_ms=command.utterance_end_ms,
            masked=tuple(spans),
        )
        await self._record.record(event)  # 마스킹 후 — command(원문)는 여기서 더 이상 쓰지 않는다
        return event
