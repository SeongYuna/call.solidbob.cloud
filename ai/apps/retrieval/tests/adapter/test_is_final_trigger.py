# Requirement: B-1
"""`TriggerPort` 구현 v1. 외부 자원을 부르지 않아 전부 ES 없이 돈다."""

from __future__ import annotations

import pytest

from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.output.trigger_port import TriggerPort
from retrieval.adapter.outbound.is_final_trigger import IsFinalTrigger
from retrieval.domain.services.trigger import STT_FINAL_LAG_MS


def event(**kw) -> TranscriptEvent:
    args = {
        "call_id": "c_001",
        "segment_id": 17,
        "speaker": "customer",
        "text": "반품하려는데 배송비는 제가 내야 하나요",
        "is_final": True,
        "utterance_end_ms": 3100,
    }
    args.update(kw)
    return TranscriptEvent(**args)


def test_포트를_실제로_구현한다():
    """`Ports(trigger=...)`·`dependency_overrides` 에 꽂히려면 ABC 를 만족해야 한다."""
    assert isinstance(IsFinalTrigger(), TriggerPort)


def test_고객_최종_전사에_발동하고_시각을_채운다():
    d = IsFinalTrigger().decide(event())
    assert d.fire is True
    assert d.at_ms == 3100 + STT_FINAL_LAG_MS


@pytest.mark.parametrize(
    "kw",
    [
        {"is_final": False},          # interim
        {"speaker": "agent"},         # 상담원 발화
        {"text": "   "},              # 빈 내용
    ],
)
def test_발동하지_않을_때는_시각도_없다(kw):
    d = IsFinalTrigger().decide(event(**kw))
    assert d.fire is False
    assert d.at_ms is None


def test_발화_종료_시각을_모르면_발동은_하되_시각은_None_이다():
    """0 을 채워 "0ms 에 발동" 이라고 거짓말하지 않는다(절대 원칙 10).

    하네스는 이걸 "발동 안 함"으로 세지만, 없는 숫자를 만드는 것보다 낫다.
    """
    d = IsFinalTrigger().decide(event(utterance_end_ms=None))
    assert d.fire is True
    assert d.at_ms is None


def test_시계를_주입하면_그_값을_쓴다():
    """실시간 경로가 붙었을 때의 통로 — 그때는 모형값이 아니라 실제 도착 시각이 들어온다."""
    d = IsFinalTrigger(now_ms=lambda: 4200).decide(event())
    assert d.at_ms == 4200


def test_지연을_바꿔_끼울_수_있다():
    assert IsFinalTrigger(lag_ms=0).decide(event()).at_ms == 3100


def test_음수_지연은_거부한다():
    with pytest.raises(ValueError):
        IsFinalTrigger(lag_ms=-1)


def test_판정에_부수효과가_없다():
    """같은 이벤트를 몇 번 넣어도 같은 답이 나온다 — 규칙 계산이라 상태가 없다."""
    t = IsFinalTrigger()
    e = event()
    assert t.decide(e) == t.decide(e) == t.decide(e)


def test_콜_미디에이터_도착_시각이_있으면_모형값_대신_그_값을_쓴다():
    """실시간 경로(`services/call-mediator`)는 STT final 을 받은 시각을 싣는다 — 그게 측정값이다."""
    d = IsFinalTrigger().decide(event(received_at_ms=3620))
    assert d.at_ms == 3620


def test_주입한_시계가_도착_시각보다_우선한다():
    assert IsFinalTrigger(now_ms=lambda: 4200).decide(event(received_at_ms=3620)).at_ms == 4200


def test_도착_시각은_발동하지_않을_때_시각을_만들지_않는다():
    d = IsFinalTrigger().decide(event(speaker="agent", received_at_ms=3620))
    assert d.fire is False
    assert d.at_ms is None
