# Requirement: D-5, E-1
from evaluation.metrics.call_temperature import CallTemperatureCase, score


def case(expected=(), calm=(), predicted=(), judged=True, call_id="c"):
    return CallTemperatureCase(call_id, frozenset(expected), frozenset(calm), frozenset(predicted), judged)


def test_튀어야_할_발화를_잡으면_재현율_정밀도가_1이다():
    s = score([case(expected={8, 16}, calm={2, 4, 6}, predicted={8, 16})])
    assert (s.tp, s.fn, s.fp, s.recall, s.precision) == (2, 0, 0, 1.0, 1.0)


def test_차분한_발화를_튀었다고_하면_거짓_경고로_센다():
    s = score([case(expected={8}, calm={2, 4}, predicted={8, 4})])
    assert s.fp == 1 and s.calm_false_alarms == 1 and s.precision == 0.5


def test_애매한_턴은_채점에서_뺀다():
    """조금 격앙된 턴(raised)은 정답에도 거짓 경고에도 넣지 않는다 — 어느 쪽에 넣느냐로 수치가 흔들리지 않게."""
    s = score([case(expected={8}, calm={2}, predicted={8, 10})])  # 10 은 raised — 어느 집합에도 없다
    assert (s.tp, s.fp, s.precision) == (1, 0, 1.0)


def test_튀어야_할_발화가_없으면_재현율은_측정_불가다():
    """「처음부터 끝까지 화난 통화」·「차분한 통화」 — 재현율을 1.0 으로 적으면 가짜 만점이다."""
    s = score([case(expected=(), calm={2, 4}, predicted=())])
    assert s.recall is None and s.precision is None and s.calm_false_alarms == 0


def test_기준선을_못_만든_통화는_0_이_아니라_판정하지_않음으로_센다():
    s = score([case(expected={8}, calm={2}, predicted=(), judged=False), case(expected={3}, calm={1}, predicted={3})])
    assert (s.judged_calls, s.unjudged_calls, s.tp, s.fn) == (1, 1, 1, 0)
