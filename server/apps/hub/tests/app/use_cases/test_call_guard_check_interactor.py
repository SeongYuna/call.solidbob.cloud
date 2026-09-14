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
