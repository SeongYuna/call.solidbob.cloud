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
    # 시계는 넷 읽힌다 — 시작 · 검색 직전 · 검색 직후 · 생성 직후 (`decisions/119` ②)
    ticks = iter([10.0, 10.0, 10.125, 10.25])
    result, _ = _run(clock=lambda: next(ticks))
    assert result.cards.internal_latency_ms == 250


def test_검색과_생성을_따로_잰다():
    """합만 남기면 「느리다」는 알아도 「어디가 느리다」를 못 짚는다 (`_project/decisions/119` ②).

    4.3절 예산이 검색 150ms·리랭킹 200ms·생성 첫 토큰 500ms 로 쪼개져 있어 구간이 맞아야 대조된다.
    """
    ticks = iter([10.0, 10.0, 10.125, 10.25])
    result, _ = _run(clock=lambda: next(ticks))
    assert result.cards.retrieval_ms == 125
    assert result.cards.generation_ms == 125
    # 합이 내부 지연과 어긋나지 않는다 — 배선 시간이 끼면 합보다 크거나 같다
    assert result.cards.retrieval_ms + result.cards.generation_ms <= result.cards.internal_latency_ms


def test_라우팅_시간은_검색_구간에_섞이지_않는다():
    """B-0 는 폐기됐지만 포트는 남아 있다 — 켜면 그 시간이 검색으로 잘못 잡히면 안 된다."""
    ticks = iter([10.0, 10.5, 10.625, 10.75])   # 0.5초를 라우팅이 먹었다고 치자
    result, _ = _run(clock=lambda: next(ticks), domain_routing=_Routing("dasan"))
    assert result.cards.retrieval_ms == 125            # 라우팅 0.5초가 안 섞였다
    assert result.cards.internal_latency_ms == 750     # 합계에는 들어 있다


def test_미발동이면_지연을_재지_않는다():
    result, _ = _run(trigger=_Trigger(fire=False))
    assert result.cards is None


def test_생성이_준_카드를_그대로_내보낸다():
    """허브가 카드를 만들거나 순서를 바꾸지 않는다 — 지어내지 않는다(B-6)."""
    only = [Card(title="X", summary="Y", source=Source(doc_id="FIN-TERM-1.1", title="X"), similarity_score=0.5)]
    result, _ = _run(generation=_Generation(cards=only))
    assert len(result.cards.cards) == 1
    assert result.cards.cards[0].source.doc_id == "FIN-TERM-1.1"


class _Record:
    """RecommendationRecordPort 스텁 — 받은 묶음을 남기고 순서대로 id 를 준다."""

    def __init__(self, ids=None, clock_log=None):
        self.ids, self.saved, self.clock_log = ids, [], clock_log

    async def record(self, cards):
        if self.clock_log is not None:
            self.clock_log.append("record")
        self.saved.append(cards)
        return tuple(self.ids) if self.ids is not None else tuple(range(100, 100 + len(cards.cards)))


def test_발동하면_저장하고_돌아온_card_id를_카드에_붙인다():
    """카드 피드백(E-1)이 가리킬 id 는 저장한 뒤에만 생긴다."""
    record = _Record()
    two = [Card(title="A", summary="a", source=Source(doc_id="D-1", title="A"), similarity_score=0.9),
           Card(title="B", summary="b", source=Source(doc_id="D-2", title="B"), similarity_score=0.8)]
    result, _ = _run(generation=_Generation(cards=two), record=record)
    assert [c.card_id for c in result.cards.cards] == [100, 101]  # 배열 순서 = rank
    assert all(c.card_id is None for c in record.saved[0].cards)  # 저장소에는 id 없는 카드가 간다


def test_내부_지연은_저장_전에_잰다():
    """DB 왕복을 4.1절 p95 채점 구간에 섞지 않는다 — 시계는 **저장 전에** 다 읽힌다.

    구간을 쪼개면서 시계가 둘 → 넷이 됐다(`decisions/119` ②). 늘어난 것은 구간 수이고,
    **저장이 채점 구간 밖이라는 성질은 그대로**다 — 그것이 이 테스트가 지키는 것이다.
    """
    log = []
    ticks = iter([10.0, 10.0, 10.125, 10.25])

    def clock():
        log.append("clock")
        return next(ticks)

    result, _ = _run(clock=clock, record=_Record(clock_log=log))
    assert log == ["clock", "clock", "clock", "clock", "record"]   # 시계가 전부 record 앞에 있다
    assert result.cards.internal_latency_ms == 250


def test_미발동이면_저장하지_않는다():
    record = _Record()
    _run(trigger=_Trigger(fire=False), record=record)
    assert record.saved == []


def test_관련문서없음도_발동이라_저장한다():
    """B-6 빈 묶음도 «발동했는데 못 찾았다» 는 기록이다(공백 리포트 재료)."""
    record = _Record()
    result, _ = _run(retrieval=_Retrieval(docs=[]), generation=_Generation(cards=[]), record=record)
    assert len(record.saved) == 1 and result.cards.cards == ()


def test_기록_포트가_없으면_card_id는_None이다():
    result, _ = _run()
    assert result.cards.cards[0].card_id is None
