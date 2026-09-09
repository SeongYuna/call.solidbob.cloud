# Requirement: B-0, B-1, B-2, B-3, B-4, B-5, B-6, QUA-1
"""스텁 포트로 파이프라인 배선만 검증한다. 검색 품질·트리거 정확도는 각 스포크가 골든셋으로 채점받는다."""

import asyncio

from hub.app.dtos import Card, RetrievedDoc, Source, TranscriptEvent
from hub.app.dtos.domain_classification_dto import DomainClassification
from hub.app.dtos.recommendation_dto import RecommendCommand
from hub.app.dtos.trigger_decision_dto import TriggerDecision
from hub.app.ports.output import DomainRoutingPort, GenerationPort, RetrievalPort, TriggerPort
from hub.app.use_cases.recommendation_interactor import RecommendationInteractor

EVENT = TranscriptEvent(call_id="c_001", segment_id=31, speaker="customer",
                        text="반품 배송비는 누가 내나요", is_final=True, utterance_end_ms=2600)
DOCS = [RetrievedDoc(doc_id="SHOP-TERM-4.1", title="반품 배송비", snippet="단순 변심은 고객 부담", score=0.91)]


class _Trigger(TriggerPort):
    def __init__(self, fire=True, at_ms=3150):
        self.fire, self.at_ms, self.calls = fire, at_ms, 0

    def decide(self, event):
        self.calls += 1
        return TriggerDecision(fire=self.fire, at_ms=self.at_ms if self.fire else None)


class _Retrieval(RetrievalPort):
    def __init__(self, docs=None):
        self.docs = DOCS if docs is None else docs
        self.calls = []

    async def retrieve(self, utterance, top_k=5):
        self.calls.append((utterance, top_k))
        return list(self.docs)


class _Generation(GenerationPort):
    def __init__(self, cards=None):
        self.cards = cards
        self.calls = []

    async def to_cards(self, utterance, docs):
        self.calls.append((utterance, len(docs)))
        if self.cards is not None:
            return list(self.cards)
        return [Card(title=d.title, summary=d.snippet, source=Source(doc_id=d.doc_id, title=d.title),
                     similarity_score=d.score) for d in docs]


class _Routing(DomainRoutingPort):
    def __init__(self, domain="shopping"):
        self.domain, self.calls = domain, 0

    async def classify(self, utterance):
        self.calls += 1
        return DomainClassification(domain=self.domain, confidence=0.93)


def _run(**kw):
    parts = dict(trigger=_Trigger(), retrieval=_Retrieval(), generation=_Generation())
    parts.update(kw)
    interactor = RecommendationInteractor(**parts)
    return asyncio.run(interactor.recommend(RecommendCommand(event=EVENT))), parts


def test_트리거가_발동하면_검색과_생성까지_간다():
    result, parts = _run()
    assert result.fired is True
    assert parts["retrieval"].calls == [("반품 배송비는 누가 내나요", 5)]
    assert parts["generation"].calls == [("반품 배송비는 누가 내나요", 1)]
    assert [c.source.doc_id for c in result.cards.cards] == ["SHOP-TERM-4.1"]


def test_트리거가_미발동이면_검색조차_하지_않는다():
    """파이프라인의 게이트. 발동 안 했는데 검색하면 트리거 지표가 의미를 잃는다."""
    result, parts = _run(trigger=_Trigger(fire=False))
    assert result.fired is False
    assert result.cards is None
    assert parts["retrieval"].calls == []
    assert parts["generation"].calls == []


def test_미발동과_관련문서없음을_구분한다():
    """cards is None(검색 안 함) 과 cards 가 빈 묶음(B-6 관련 문서 없음)은 다른 상태다."""
    none_result, _ = _run(trigger=_Trigger(fire=False))
    empty_result, _ = _run(retrieval=_Retrieval(docs=[]), generation=_Generation(cards=[]))
    assert none_result.cards is None
    assert empty_result.cards is not None
    assert empty_result.cards.no_relevant_document is True


def test_트리거_발동_시각을_카드에_싣는다():
    result, _ = _run()
    assert result.cards.trigger_at_ms == 3150


def test_도메인_라우팅이_있으면_판정해서_싣는다():
    result, parts = _run(domain_routing=_Routing("shopping"))
    assert parts["domain_routing"].calls == 1
    assert result.domain == "shopping"


def test_도메인_라우팅이_없으면_건너뛰고_그대로_검색한다():
    """decisions/007 의 '신뢰도 낮으면 전 도메인 검색' 폴백이 항상 켜진 상태와 같다."""
    result, parts = _run(domain_routing=None)
    assert result.domain is None
    assert parts["retrieval"].calls != []  # 검색은 그대로 돈다


def test_내부_지연을_잰다():
    """4.1절 p95 ≤1,000ms 채점 재료. 트리거 발동 → 카드 완성 구간."""
    ticks = iter([10.0, 10.25])
    result, _ = _run(clock=lambda: next(ticks))
    assert result.cards.internal_latency_ms == 250


def test_미발동이면_지연을_재지_않는다():
    result, _ = _run(trigger=_Trigger(fire=False))
    assert result.cards is None


def test_생성이_준_카드를_그대로_내보낸다():
    """허브가 카드를 만들거나 순서를 바꾸지 않는다 — 지어내지 않는다(B-6)."""
    only = [Card(title="X", summary="Y", source=Source(doc_id="FIN-TERM-1.1", title="X"), similarity_score=0.5)]
    result, _ = _run(generation=_Generation(cards=only))
    assert len(result.cards.cards) == 1
    assert result.cards.cards[0].source.doc_id == "FIN-TERM-1.1"
