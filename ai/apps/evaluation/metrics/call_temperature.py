# Requirement: D-5, E-1
"""D-5 통화 온도 채점 — **튀어야 할 발화를 튀었다고 했는가, 차분한 발화를 튀었다고 하지 않았는가.**

판정은 `voice_signal`(규칙 — 화자별 중앙값·MAD 로버스트 z)이 하고, 여기서는 그 결과를 정답과 대조만 한다.
LLM 을 쓰지 않는다(6.2절 원칙 1). `.importlinter` 계약 2 때문에 `voice_signal` 을 import 하지 않는다 —
판정 결과(`segment_id` 집합)만 받는다.

**세 가지 턴으로 가른다.** 정답이 「튀어야 함」·「튀면 안 됨」 둘뿐이면 애매한 턴(조금 격앙된 말투)이 어느 쪽에
들어가느냐로 수치가 흔들린다 — 그런 턴은 **채점에서 뺀다**(`excluded`). 섞어서 좋게 보이게 하지 않는다.

**기준선을 못 만든 통화는 0 으로 세지 않는다.** 「튄 구간 없음」과 「판정하지 않음」은 다르다(절대 원칙 10) —
`judged=False` 인 통화는 재현율·정밀도 분모에서 빠지고 따로 센다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CallTemperatureCase:
    """통화 1건·화자 1명의 정답과 판정."""

    call_id: str
    expected_outliers: frozenset[int]   # 튀어야 할 발화
    calm: frozenset[int]                # 튀면 안 되는 발화
    predicted_outliers: frozenset[int]  # 규칙이 튀었다고 한 발화
    judged: bool                        # 기준선을 만들었는가(발화 수 부족이면 False)


@dataclass(frozen=True)
class CallTemperatureScore:
    tp: int
    fn: int
    fp: int
    recall: float | None      # 튀어야 할 발화가 0건이면 None — 0 도 1 도 아니다
    precision: float | None   # 튀었다고 한 것이 0건이면 None
    calm_false_alarms: int    # 차분한 발화를 튀었다고 한 수 — 상담원 화면에 거짓 경고가 뜬 수
    judged_calls: int
    unjudged_calls: int


def score(cases: list[CallTemperatureCase]) -> CallTemperatureScore:
    tp = fn = fp = calm_fp = judged = unjudged = 0
    for c in cases:
        if not c.judged:
            unjudged += 1
            continue
        judged += 1
        tp += len(c.expected_outliers & c.predicted_outliers)
        fn += len(c.expected_outliers - c.predicted_outliers)
        # 정밀도 분모는 「튀어야 함」·「튀면 안 됨」 로 라벨이 있는 턴만 — 채점에서 뺀 애매한 턴은 넣지 않는다
        wrong = (c.predicted_outliers & c.calm) - c.expected_outliers
        fp += len(wrong)
        calm_fp += len(wrong)
    return CallTemperatureScore(
        tp=tp,
        fn=fn,
        fp=fp,
        recall=tp / (tp + fn) if tp + fn else None,
        precision=tp / (tp + fp) if tp + fp else None,
        calm_false_alarms=calm_fp,
        judged_calls=judged,
        unjudged_calls=unjudged,
    )
