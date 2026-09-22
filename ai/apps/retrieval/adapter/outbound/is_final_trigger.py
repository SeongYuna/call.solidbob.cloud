# Requirement: B-1, B-6
"""`TriggerPort` 구현 v1 — `is_final` 도착 기반.

판정 규칙 자체는 `retrieval.domain.services.trigger` 에 있고 여기는 계약 DTO 로 옮기기만 한다
(`ai/CLAUDE.md` 4번 — 알고리즘은 domain, 배선은 adapter).

`RetrievalPort` 와 달리 **동기 함수**다. 규칙 계산뿐이라 외부 자원을 부르지 않는다
(`TriggerPort.decide` 가 `def` 인 이유).

## `at_ms` 를 무엇으로 채우는가 — 읽고 넘어갈 것

우선순위는 셋이다.

1. `now_ms` 시계를 주입했으면 그 값
2. **`TranscriptEvent.received_at_ms`** — 콜 미디에이터가 STT final 을 받은 시각(통화 기준 ms).
   실시간 경로(`services/call-mediator`)가 채운다(2026-09-14, `w4-trigger-arrival-time`). 이게 **측정값**이다
3. 둘 다 없으면 "발화 종료 + STT 최종 결과 지연(V4 실측 346ms)"으로 **모형화**한다

골든셋·배치에는 도착 시각이 없어 3번으로 떨어지고, 그 지연 분포는 **상수 하나로 수렴한다**
(p50 = p95 = 346). 숫자가 나오지만 측정이 아니다 — 그래서 `scripts/run_eval.py` 는 트리거 포트를
**꽂지 않고** 하네스가 "측정 불가"로 보고하게 둔다(절대 원칙 10). 서버 경로에는 꽂는다 — 거기서는
발동 여부(fire) 자체가 파이프라인을 흐르게 하는 데 필요하고, 그건 진짜 판정이기 때문이다.
"""

from __future__ import annotations

from typing import Callable

from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.dtos.trigger_decision_dto import TriggerDecision
from hub.app.ports.output.trigger_port import TriggerPort

from retrieval.domain.services.backchannel import is_backchannel
from retrieval.domain.services.trigger import STT_FINAL_LAG_MS, fire_at_ms, should_fire

# 맞장구·인사·감사·끝인사 억제(`decisions/216`)의 기본값. 결정 기록의 채택 여부를 따른다.
SUPPRESS_BACKCHANNEL_DEFAULT = False


class IsFinalTrigger(TriggerPort):
    """고객의 `is_final` 전사가 도착하면 발동한다.

    발동 시각은 `now_ms` 시계 → 이벤트의 `received_at_ms` → `utterance_end_ms + lag_ms` 모형 순으로 정한다(위 주석).
    """

    def __init__(
        self,
        *,
        lag_ms: int = STT_FINAL_LAG_MS,
        now_ms: Callable[[], int] | None = None,  # 통화 기준 ms 를 돌려주는 시계
        suppress_backchannel: bool = SUPPRESS_BACKCHANNEL_DEFAULT,
    ) -> None:
        if lag_ms < 0:
            raise ValueError(f"lag_ms 는 음수일 수 없다: {lag_ms}")
        self._lag_ms = lag_ms
        self._now_ms = now_ms
        # 켜면 맞장구·인사·감사·끝인사로만 된 발화는 발동하지 않는다(`fired: false` — 검색·카드 없음).
        # 규칙은 문자열 판정뿐이다(점수 문턱 없음). 발동한 턴의 질의·검색은 바꾸지 않는다.
        self._suppress_backchannel = suppress_backchannel

    def decide(self, event: TranscriptEvent) -> TriggerDecision:
        if not should_fire(is_final=event.is_final, speaker=event.speaker, text=event.text):
            return TriggerDecision(fire=False)
        if self._suppress_backchannel and is_backchannel(event.text):
            return TriggerDecision(fire=False)  # decisions/216 — 검색할 내용이 없는 발화

        if self._now_ms:
            at_ms = self._now_ms()
        elif event.received_at_ms is not None:
            at_ms = event.received_at_ms
        else:
            at_ms = fire_at_ms(event.utterance_end_ms, lag_ms=self._lag_ms)
        if at_ms is None:
            # 발동은 맞는데 시각을 모른다. 지어내지 않는다 — 하네스는 이걸 "발동 안 함"으로
            # 세지만, 그게 "0ms 에 발동했다"고 거짓말하는 것보다 낫다(절대 원칙 10).
            return TriggerDecision(fire=True, at_ms=None)
        return TriggerDecision(fire=True, at_ms=at_ms)
