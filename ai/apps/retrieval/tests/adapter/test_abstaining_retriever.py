# Requirement: B-6, QUA-1
"""수동 검색 기권(`_project/decisions/135`) — 1순위가 문턱 아래면 「관련 문서 없음」.

수동 QA Q-44: `ㅁㄴㅇㄹ` 같은 무의미 입력에 결과 4건이 붙었다. 자동 추천 쪽 문턱은 보류(`215`)라
이 자리에만 건다.
"""
import asyncio

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort
from retrieval.adapter.outbound.abstaining_retriever import AbstainingRetriever


class _Fixed(RetrievalPort):
    def __init__(self, *scores: float) -> None:
        self.scores = scores
        self.calls: list[tuple[str, int]] = []

    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        self.calls.append((utterance, top_k))
        return [
            RetrievedDoc(doc_id=f"D-{i}", title="t", snippet="s", score=s)
            for i, s in enumerate(self.scores[:top_k])
        ]


def _run(inner, utterance="ㅁㄴㅇㄹ", top_k=5, min_score=0.67):
    return asyncio.run(AbstainingRetriever(inner, min_score=min_score).retrieve(utterance, top_k=top_k))


def test_문턱_아래면_한_건도_돌려주지_않는다():
    assert _run(_Fixed(0.61, 0.60, 0.58)) == []


def test_문턱_위면_그대로_돌려준다():
    docs = _run(_Fixed(0.71, 0.40), utterance="전입신고 구비서류")
    assert [d.doc_id for d in docs] == ["D-0", "D-1"]  # 2순위가 낮아도 자르지 않는다 — 1순위만 본다


def test_문턱과_같으면_통과한다():
    """`< 문턱` 만 기권이다 — 잰 값이 경계 포함이라 여기서 부등호를 바꾸지 않는다(decisions/215)."""
    assert len(_run(_Fixed(0.67))) == 1


def test_앞_검색이_0건이면_그대로_0건이다():
    """0건은 「벡터가 없다」는 뜻이라 기권과 다르다 — 세지 않는다(FallbackRetriever 가 BM25 로 내려간 뒤일 수 있다)."""
    inner = _Fixed()
    r = AbstainingRetriever(inner, min_score=0.67)
    assert asyncio.run(r.retrieve("무엇")) == [] and r.abstentions == 0


def test_기권_횟수를_센다():
    r = AbstainingRetriever(_Fixed(0.10), min_score=0.67)
    asyncio.run(r.retrieve("ㅁㄴㅇㄹ"))
    asyncio.run(r.retrieve("ㅋㅋㅋ"))
    assert r.abstentions == 2


def test_질의와_top_k를_그대로_넘긴다():
    inner = _Fixed(0.9, 0.8, 0.7)
    _run(inner, utterance="전입신고", top_k=2)
    assert inner.calls == [("전입신고", 2)]
