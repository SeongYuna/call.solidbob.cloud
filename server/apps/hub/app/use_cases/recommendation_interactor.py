# Requirement: B-0, B-1, B-2, B-3, B-4, B-5, B-6
"""추천 파이프라인 — 포트를 순서대로 부르는 것이 전부다. 판정은 하나도 하지 않는다.

    TriggerPort(B-1) ─fire?─▶ DomainRoutingPort(B-0) ─▶ RetrievalPort(B-2·B-3) ─▶ GenerationPort(B-4~B-6)

**여기서 하지 않는 것**(절대 원칙 9 — 판정은 규칙이, 설명만 LLM이):
- 발동 여부를 `if` 로 다시 판단하지 않는다. `TriggerDecision.fire` 를 그대로 따른다.
- 검색 결과 순서를 다시 매기지 않는다. 리랭킹은 retrieval 스포크 몫이다.
- 카드를 지어내지 않는다. 생성이 빈 목록을 주면 "관련 문서 없음"(B-6)으로 그대로 나간다.

`internal_latency_ms` 는 **트리거 발동 시점부터 카드 완성까지**다([4.1절](/docs/04/) p95 ≤1,000ms 채점 재료).
발화 종료 → 화면 표시(e2e)는 콜 미디에이터·대시보드가 채운다. **저장은 잰 뒤에 한다** — DB 왕복을 내부 지연에 섞지 않는다.

발동한 추천은 기록 포트로 남기고 돌아온 `card_id` 를 카드에 붙인다(카드 피드백 E-1 이 그 값으로 카드를 가리킨다).
기록 포트가 없으면(스텁 조립) 저장하지 않고 `card_id` 는 None 이다.
"""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter
from typing import Callable

from hub.app.dtos.recommendation_card_dto import RecommendationCards
from hub.app.dtos.recommendation_dto import RecommendCommand, RecommendResult
from hub.app.ports.input.recommendation_use_case import RecommendationUseCase
from hub.app.ports.output.domain_routing_port import DomainRoutingPort
from hub.app.ports.output.generation_port import GenerationPort
from hub.app.ports.output.recommendation_record_port import RecommendationRecordPort
from hub.app.ports.output.retrieval_port import RetrievalPort
from hub.app.ports.output.trigger_port import TriggerPort


class RecommendationInteractor(RecommendationUseCase):
    def __init__(
        self,
        trigger: TriggerPort,
        retrieval: RetrievalPort,
        generation: GenerationPort,
        domain_routing: DomainRoutingPort | None = None,
        clock: Callable[[], float] = perf_counter,
        record: RecommendationRecordPort | None = None,
    ) -> None:
        self._trigger = trigger
        self._retrieval = retrieval
        self._generation = generation
        # B-0 는 선택이다. 스포크가 없으면 도메인을 정하지 않고 전 도메인을 검색한다
        # (decisions/007 의 "신뢰도 낮으면 4개 인덱스 전체 검색" 폴백과 같은 상태).
        self._domain_routing = domain_routing
        self._clock = clock
        self._record = record

    async def recommend(self, command: RecommendCommand) -> RecommendResult:
        event = command.event

        decision = self._trigger.decide(event)
        if not decision.fire:
            return RecommendResult(fired=False)  # 검색조차 하지 않는다

        started = self._clock()

        domain = None
        if self._domain_routing is not None:
            domain = (await self._domain_routing.classify(event.text)).domain

        docs = await self._retrieval.retrieve(event.text, top_k=command.top_k)
        cards = await self._generation.to_cards(event.text, docs)

        elapsed_ms = int((self._clock() - started) * 1000)
        batch = RecommendationCards(
            call_id=event.call_id,
            trigger_at_ms=decision.at_ms or 0,
            cards=tuple(cards),
            internal_latency_ms=elapsed_ms,
        )
        if self._record is not None:
            card_ids = await self._record.record(batch)
            batch = replace(batch, cards=tuple(replace(c, card_id=i) for c, i in zip(batch.cards, card_ids, strict=True)))
        return RecommendResult(fired=True, domain=domain, cards=batch)
