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


# ── C-6 콜 가드 — 마스킹 뒤에, 고객 확정 발화에만 ────────────────────────────────────

import pytest  # noqa: E402

from hub.app.dtos import CallGuardFlag  # noqa: E402
from hub.app.ports.output import CallGuardPort, CallGuardRecordPort  # noqa: E402


class _SpyGuard(CallGuardPort):
    def __init__(self):
        self.inputs: list[str] = []

    async def detect(self, customer_utterance: str):
        self.inputs.append(customer_utterance)
        idx = customer_utterance.find("바보")
        return [] if idx < 0 else [CallGuardFlag(category="insult", phrase="바보", span_start=idx, span_end=idx + 2)]


class _SpyGuardRecord(CallGuardRecordPort):
    def __init__(self, record: _SpyRecord | None = None):
        self.calls = []
        self._record = record

    async def replace(self, call_id, segment_id, flags):
        # 발화 행이 먼저 저장돼 있어야 외래키가 선다
        assert self._record is None or any(e.segment_id == segment_id for e in self._record.events)
        self.calls.append((call_id, segment_id, list(flags)))


def _ingest(interactor, **kw):
    base = dict(call_id="c_001", segment_id=5, speaker="customer", raw_text="카드번호 1234 이 바보야", is_final=True)
    base.update(kw)
    return asyncio.run(interactor.ingest(TranscriptIngestCommand(**base)))


def test_콜_가드는_마스킹된_자막을_받고_원문은_받지_않는다():
    """MANUAL-5.5 — 폭언 기록에 개인정보를 남기지 않는다. 구조로 막는다."""
    record, guard = _SpyRecord(), _SpyGuard()
    guard_record = _SpyGuardRecord(record)
    event = _ingest(TranscriptIngestInteractor(_StubMasking(), record, guard, guard_record))

    assert guard.inputs == [event.text] and "1234" not in guard.inputs[0]
    [(call_id, segment_id, [flag])] = guard_record.calls
    assert (call_id, segment_id) == ("c_001", 5)
    assert event.text[flag.span_start:flag.span_end] == flag.phrase  # 구간이 저장된 자막을 가리킨다


def test_걸린_것이_없어도_기록을_갈아끼운다():
    guard_record = _SpyGuardRecord()
    _ingest(TranscriptIngestInteractor(_StubMasking(), _SpyRecord(), _SpyGuard(), guard_record), raw_text="서류 문의요")
    assert guard_record.calls == [("c_001", 5, [])]


@pytest.mark.parametrize("kw", [dict(speaker="agent"), dict(is_final=False)])
def test_상담원_발화와_interim_에는_콜_가드를_걸지_않는다(kw):
    guard, guard_record = _SpyGuard(), _SpyGuardRecord()
    _ingest(TranscriptIngestInteractor(_StubMasking(), _SpyRecord(), guard, guard_record), **kw)
    assert guard.inputs == [] and guard_record.calls == []


def test_탐지와_기록은_함께_주어야_한다():
    with pytest.raises(ValueError):
        TranscriptIngestInteractor(_StubMasking(), _SpyRecord(), call_guard=_SpyGuard())
    with pytest.raises(ValueError):
        TranscriptIngestInteractor(_StubMasking(), _SpyRecord(), call_guard_record=_SpyGuardRecord())
