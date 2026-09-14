# Requirement: C-6, QUA-1
"""어댑터가 hub 계약으로 옮길 때 **구간이 넘겨받은 문자열 기준**인지 고정한다 — 저장(`call_guard_flag`)이
그 구간으로 자막을 가리키기 때문이다."""

import asyncio

from call_guard.adapter.outbound.rule_call_guard_adapter import RuleCallGuardAdapter
from call_guard.domain.services.detector import detect


def test_구간이_넘겨받은_문자열에서_phrase_를_정확히_가리킨다():
    text = "제 번호는 *********** 인데 이 개새끼야 가만 안 둬"
    flags = asyncio.run(RuleCallGuardAdapter().detect(text))
    assert flags, "걸린 것이 있어야 한다"
    for f in flags:
        assert f.span_start is not None and f.span_end is not None
        assert text[f.span_start : f.span_end] == f.phrase


def test_앞뒤_공백이_있어도_구간이_밀리지_않는다():
    """전에는 탐지기가 `strip()` 한 문자열 기준으로 오프셋을 냈다 — 앞 공백 수만큼 저장 구간이 밀린다."""
    text = "   이 개새끼야  "
    [d] = detect(text)
    assert text[d.start : d.end] == d.phrase == "개새끼"


def test_공백뿐인_발화는_탐지하지_않는다():
    assert detect("   ") == []
