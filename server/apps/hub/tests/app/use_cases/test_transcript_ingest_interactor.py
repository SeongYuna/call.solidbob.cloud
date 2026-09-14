# Requirement: 7.3절 전사 이벤트, C-5, SEC-1, QUA-1
"""스텁 포트로 인터랙터만 검증. 진짜 마스킹은 masking 스포크가 골든셋으로 채점받는다."""

import asyncio

from hub.app.dtos import MaskedSpan, TranscriptEvent, TranscriptIngestCommand
from hub.app.ports.output import MaskingPort, TranscriptIngestRecordPort
from hub.app.use_cases.transcript_ingest_interactor import TranscriptIngestInteractor


class _StubMasking(MaskingPort):
    """'1234'를 '****'로 바꾸는 척만 한다 — 위치 계산 검증용."""

    def mask(self, text: str):
        idx = text.find("1234")
        if idx < 0:
            return text, ()
        return text[:idx] + "****" + text[idx + 4:], (MaskedSpan(type="P2", span=(idx, idx + 4)),)


class _SpyRecord(TranscriptIngestRecordPort):
    def __init__(self):
        self.events: list[TranscriptEvent] = []

    async def record(self, event: TranscriptEvent) -> None:
        self.events.append(event)


def test_ingest_masks_before_record():
    record = _SpyRecord()
    interactor = TranscriptIngestInteractor(masking=_StubMasking(), record=record)
    event = asyncio.run(interactor.ingest(TranscriptIngestCommand(
        call_id="c_001", segment_id=1, speaker="customer", raw_text="카드번호는 1234 입니다",
        is_final=True, utterance_end_ms=3100,
    )))
    assert event.text == "카드번호는 **** 입니다"
    assert event.masked[0].type == "P2" and event.text[slice(*event.masked[0].span)] == "****"
    assert record.events == [event]  # 기록 포트는 마스킹 후 이벤트만 받는다
    assert "1234" not in record.events[0].text


def test_ingest_without_pii_passes_through_with_empty_spans():
    record = _SpyRecord()
    event = asyncio.run(TranscriptIngestInteractor(_StubMasking(), record).ingest(TranscriptIngestCommand(
        call_id="c_001", segment_id=2, speaker="agent", raw_text="네 확인해드릴게요", is_final=False,
    )))
    assert event.text == "네 확인해드릴게요" and event.masked == () and event.utterance_end_ms is None
