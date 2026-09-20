# Requirement: C-6, QUA-1
"""스텁 포트로 배선만 검증. 실제 탐지 성능은 call_guard 스포크가 골든셋으로 채점받는다(ai/ 평가 하네스)."""

import asyncio

import pytest

from hub.app.dtos.call_guard_check_dto import CallGuardCheckCommand
from hub.app.dtos.call_guard_dto import CallGuardFlag
from hub.app.ports.output.call_guard_flag_record_port import CallGuardFlagRecordPort
from hub.app.ports.output.call_guard_port import CallGuardPort
from hub.app.use_cases.call_guard_check_interactor import CallGuardCheckInteractor

INSULT = CallGuardFlag(category="insult", phrase="병신", source_doc_id="DASAN-MANUAL-5.1", span=(4, 6))
DISTRESS = CallGuardFlag(category="distress", phrase="죽고 싶어요", source_doc_id="DASAN-MANUAL-5.4", span=(0, 6))


class _Guard(CallGuardPort):
    def __init__(self, flags=None):
        self.flags = [] if flags is None else flags
        self.calls = []

    async def detect(self, customer_utterance):
        self.calls.append(customer_utterance)
        return list(self.flags)


class _Record(CallGuardFlagRecordPort):
    def __init__(self):
        self.calls = []

    async def record(self, call_id, segment_id, flags):
        self.calls.append((call_id, segment_id, flags))


def _run(guard, record, utterance="이런 병신 같은"):
    cmd = CallGuardCheckCommand(call_id="c_001", segment_id=7, customer_utterance=utterance)
    return asyncio.run(CallGuardCheckInteractor(call_guard=guard, record=record).check(cmd))


def test_고객_발화를_자르지_않고_포트에_넘긴다():
    """span 이 받은 문자열 기준이어야 자막과 맞는다 — 앞뒤 공백도 그대로 넘긴다."""
    guard = _Guard()
    _run(guard, _Record(), " 이런 병신 같은 ")
    assert guard.calls == [" 이런 병신 같은 "]


def test_잡힌_신호를_기록하고_그대로_돌려준다():
    record = _Record()
    result = _run(_Guard([INSULT, DISTRESS]), record)
    assert result.flags == (INSULT, DISTRESS)
    assert record.calls == [("c_001", 7, (INSULT, DISTRESS))]


def test_잡힌_것이_없으면_기록하지_않고_빈_목록이다():
    """'잡힌 것이 없음'이지 '안전함'이 아니다 — 등급·점수 필드가 없다 (부록 A-1)."""
    record = _Record()
    result = _run(_Guard([]), record)
    assert result.flags == ()
    assert record.calls == []
    assert not hasattr(result, "risk_score") and not hasattr(result, "safe")


@pytest.mark.parametrize("utterance", ["", "   "])
def test_빈_발화는_거부한다(utterance):
    guard = _Guard([INSULT])
    with pytest.raises(ValueError):
        _run(guard, _Record(), utterance)
    assert guard.calls == []


# ─────────────────────────────── 저장 실패 — 컴플라이언스와 같은 규칙 (2026-09-20)

class _FailingRecord(CallGuardFlagRecordPort):
    def __init__(self, error):
        self._error, self.calls = error, 0

    async def record(self, call_id, segment_id, flags):
        self.calls += 1
        raise self._error


@pytest.mark.parametrize("failure", [RuntimeError("db down"), ConnectionError("pg unreachable")])
def test_저장이_우리_쪽_사정으로_실패해도_탐지_결과는_돌려준다(failure):
    """전에는 500 이었다 — DB 가 잠깐 흔들리면 **상담원을 보호하려는 경고가 화면에서도 사라졌다.**

    탐지는 성공했다. 기록 실패는 로그로 남기고 응답은 그대로 내보낸다(컴플라이언스와 같은 규칙).
    """
    record = _FailingRecord(failure)
    result = _run(_Guard([INSULT]), record)
    assert result.flags == (INSULT,)   # 잡힌 신호가 그대로 나간다
    assert record.calls == 1


def test_없는_전사_구간을_가리키면_삼키지_않는다():
    """호출자의 순서 실수다 — 라우터가 404 로 돌려준다. 삼키면 「저장된 줄 알았는데 0행」이 조용히 이어진다."""
    from hub.app.ports.output.transcript_ingest_record_port import SegmentNotFoundError

    with pytest.raises(SegmentNotFoundError):
        _run(_Guard([INSULT]), _FailingRecord(SegmentNotFoundError("c_001", 7)))


def test_스포크가_span_을_안_채운_결함은_삼키지_않는다():
    """기다려도 낫지 않는 **우리 결함**이다 — 로그 한 줄 뒤에 숨기지 않고 500 으로 드러낸다."""
    from hub.app.ports.output.call_guard_flag_record_port import CallGuardFlagSpanMissingError

    with pytest.raises(CallGuardFlagSpanMissingError):
        _run(_Guard([INSULT]), _FailingRecord(CallGuardFlagSpanMissingError("span 없음")))
