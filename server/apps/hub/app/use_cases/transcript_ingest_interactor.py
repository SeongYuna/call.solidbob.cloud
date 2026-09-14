# Requirement: 7.3절 전사 이벤트, C-5, C-6, SEC-1
"""전사 수신 인터랙터 — 파이프라인의 입구. 원문이 살아 있는 구간은 이 함수의 첫 두 줄뿐이다.

**C-6 콜 가드는 마스킹 뒤에 돈다.** 탐지기에 넘기는 것은 `event.text`(마스킹 완료본)이지
`command.raw_text` 가 아니다 — 그래서 `call_guard_flag.phrase` 에 개인정보가 들어갈 경로가 없다
(`DASAN-MANUAL-5.5`). 순서를 바꾸면 폭언 기록에 전화번호가 남는다.

콜 가드를 **고객의 확정 발화에만** 거는 것은 판정이 아니라 배선이다 — 상담원 발화는 C-1~C-4 의
대상이고(화자가 반대다, `decisions/201`), interim 은 `transcript_segment` 에 저장되지 않아
외래키가 설 행이 없다(7.3절).
"""

from __future__ import annotations

from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.dtos.transcript_ingest_dto import TranscriptIngestCommand
from hub.app.ports.input.transcript_ingest_use_case import TranscriptIngestUseCase
from hub.app.ports.output.call_guard_port import CallGuardPort
from hub.app.ports.output.call_guard_record_port import CallGuardRecordPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.transcript_ingest_record_port import TranscriptIngestRecordPort


class TranscriptIngestInteractor(TranscriptIngestUseCase):
    def __init__(
        self,
        masking: MaskingPort,
        record: TranscriptIngestRecordPort,
        call_guard: CallGuardPort | None = None,
        call_guard_record: CallGuardRecordPort | None = None,
    ) -> None:
        if (call_guard is None) != (call_guard_record is None):
            # 탐지만 있고 기록이 없으면 출력이 버려지고, 기록만 있으면 부를 것이 없다
            raise ValueError("call_guard 와 call_guard_record 는 함께 주거나 함께 비워야 합니다")
        self._masking = masking
        self._record = record
        self._call_guard = call_guard
        self._call_guard_record = call_guard_record

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

        if self._call_guard is not None and event.is_final and event.speaker == "customer":
            # 발화 행이 저장된 뒤라야 call_guard_flag 의 복합 외래키가 선다
            flags = await self._call_guard.detect(event.text)
            await self._call_guard_record.replace(event.call_id, event.segment_id, flags)
        return event
