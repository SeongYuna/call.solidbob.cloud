# Requirement: D-5, QUA-1
"""판정 결과를 기록 포트로 넘기는 규칙 — **판정하지 않았으면 부르지 않는다**(절대 원칙 10)."""

import asyncio

from hub.app.ports.output.voice_outlier_record_port import VoiceOutlierRecordPort

from voice_signal.adapter.outbound.voice_outlier_recorder import record_speaker_temperature
from voice_signal.domain.services.outlier import MIN_BASELINE_UTTERANCES


class _Spy(VoiceOutlierRecordPort):
    def __init__(self):
        self.calls = []

    async def replace(self, call_id, speaker, outliers):
        self.calls.append((call_id, speaker, list(outliers)))


def test_튄_발화가_segment_id_와_함께_저장된다():
    spy = _Spy()
    samples = [(sid, 180.0 + (sid % 2)) for sid in range(1, 16)] + [(40, 430.0)]
    saved = asyncio.run(record_speaker_temperature(spy, "c_001", "customer", samples))
    assert saved is True
    [(call_id, speaker, outliers)] = spy.calls
    assert (call_id, speaker) == ("c_001", "customer")
    assert [(o.segment_id, o.speaker, o.baseline_n) for o in outliers] == [(40, "customer", 16)]


def test_튄_구간이_없어도_판정했으면_빈_목록으로_갈아끼운다():
    """「이제 튄 구간이 없다」도 갱신이다 — 앞 판정이 남아 있으면 옛 기준선의 결과가 섞인다."""
    spy = _Spy()
    samples = [(sid, 180.0 + (sid % 2)) for sid in range(1, 16)]
    assert asyncio.run(record_speaker_temperature(spy, "c_001", "agent", samples)) is True
    assert spy.calls == [("c_001", "agent", [])]


def test_기준선을_못_만들면_포트를_부르지_않는다():
    spy = _Spy()
    samples = [(sid, 180.0) for sid in range(MIN_BASELINE_UTTERANCES - 1)]
    assert asyncio.run(record_speaker_temperature(spy, "c_001", "customer", samples)) is False
    assert spy.calls == []
