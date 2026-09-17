# Requirement: B-2
"""BM25 검색 어댑터 (w2-naive-rag).

ES 없이 도는 절반은 **가짜 클라이언트**로 질의 모양과 응답 변환을 고정한다. CI 가 이걸 돌린다.
`@pytest.mark.integration` 은 실제 ES 가 있을 때만 — 색인이 적재돼 있어야 한다
(`scripts/index_knowledge_base.py --to-es --recreate`).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from retrieval.adapter.outbound import es_index
from retrieval.adapter.outbound.es_bm25_retriever import SEARCH_FIELDS, EsBm25Retriever
from retrieval.adapter.outbound.knowledge_base_loader import load_chunks
from retrieval.domain.value_objects.chunk import NON_RECOMMENDABLE_DOC_TYPES

KB_ROOT = Path(__file__).resolve().parents[4].parent / "knowledge-base"


class FakeClient:
    """`search()` 호출 인자를 붙잡아 두고 정해진 응답을 돌려준다."""

    def __init__(self, hits: list[dict] | None = None):
        self.calls: list[dict] = []
        self._hits = hits or []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return {"hits": {"hits": self._hits}}


def _hit(doc_id="FIN-TERM-2.2", chunk_id=None, score=9.9):
    return {
        "_id": chunk_id or doc_id,
        "_score": score,
        "_source": {"doc_id": doc_id, "title": "보상 기준", "text": "본문", "domain": "finance"},
    }


# ─────────────────────────────────────── ES 없이 도는 것

def _match(q):
    return q["bool"]["must"][0]["multi_match"]


def test_질의는_title_과_text_를_함께_본다():
    q = EsBm25Retriever(FakeClient()).build_query("반품 배송비")
    assert _match(q)["query"] == "반품 배송비"
    assert _match(q)["fields"] == list(SEARCH_FIELDS)


def test_내부_규정_조항은_후보에서_뺀다():
    """2026-09-17 로컬 E2E — 「F-2 가 적용되지 않는 이유」(POLICY) 가 인감증명 통화의 1순위 카드가 돼
    필요서류 판정이 0건이었다. 상담원에게 보일 내용이 아니고 골든셋 정답에도 없다(97건 중 0).
    must_not 이라 점수를 바꾸지 않고 후보만 줄인다."""
    q = EsBm25Retriever(FakeClient()).build_query("인감증명 대리")
    assert q["bool"]["must_not"] == [{"terms": {"doc_type": list(NON_RECOMMENDABLE_DOC_TYPES)}}]
    assert "POLICY" in NON_RECOMMENDABLE_DOC_TYPES and "TERM" not in NON_RECOMMENDABLE_DOC_TYPES


def test_필드_가중치를_주지_않는다():
    """베이스라인이라 튜닝을 넣지 않는다 — 4주차에 붙이고 그 차이를 잰다."""
    assert all("^" not in f for f in SEARCH_FIELDS)


def test_도메인을_주면_filter_로_좁힌다():
    q = EsBm25Retriever(FakeClient(), domain="shopping").build_query("반품")
    assert q["bool"]["filter"] == [{"term": {"domain": "shopping"}}]
    # filter 절이라 점수에 영향을 주지 않는다 — must 안의 질의만 점수를 만든다
    assert _match(q)["query"] == "반품"


def test_기본은_도메인을_좁히지_않는다():
    """포트 시그니처에 도메인이 없어서 하네스가 넘겨줄 방법이 없다 — 4개 도메인 전체를 본다."""
    assert "filter" not in EsBm25Retriever(FakeClient()).build_query("반품")["bool"]


def test_top_k_와_인덱스가_그대로_넘어간다():
    c = FakeClient()
    asyncio.run(EsBm25Retriever(c, index="callguard-kb-single").retrieve("환불", top_k=3))
    assert c.calls[0]["size"] == 3
    assert c.calls[0]["index"] == "callguard-kb-single"


def test_같은_조항의_청크가_자리를_나눠먹지_않는다():
    """채점 단위가 doc_id 라, 쪼개진 청크 둘이 top_k 두 칸을 차지하면 후보가 줄어든다."""
    c = FakeClient()
    asyncio.run(EsBm25Retriever(c).retrieve("환불"))
    assert c.calls[0]["collapse"] == {"field": "doc_id"}


def test_응답을_계약_DTO_로_바꾼다():
    c = FakeClient([_hit(doc_id="SHOP-TERM-4.2", score=9.98)])
    docs = asyncio.run(EsBm25Retriever(c).retrieve("반품 배송비"))
    assert [(d.doc_id, d.title, d.score) for d in docs] == [("SHOP-TERM-4.2", "보상 기준", 9.98)]
    assert docs[0].snippet == "본문"


def test_분할된_청크도_doc_id_는_조항_ID_다():
    """`_id` 는 `FIN-TERM-3.2#1` 이지만 채점은 조항 ID 로 한다."""
    c = FakeClient([_hit(doc_id="FIN-TERM-3.2", chunk_id="FIN-TERM-3.2#1")])
    assert asyncio.run(EsBm25Retriever(c).retrieve("해지"))[0].doc_id == "FIN-TERM-3.2"


@pytest.mark.parametrize("utterance", ["", "   ", "\n"])
def test_빈_발화는_검색하지_않는다(utterance):
    """억지로 카드를 채우지 않는다 — 근거가 없으면 "관련 문서 없음"이 맞다(B-6)."""
    c = FakeClient([_hit()])
    assert asyncio.run(EsBm25Retriever(c).retrieve(utterance)) == []
    assert c.calls == []


# ─────────────────────────────────────── 실제 ES 가 있을 때만

@pytest.fixture(scope="module")
def client():
    url = os.environ.get("ELASTICSEARCH_URL")
    if not url:
        pytest.skip("ELASTICSEARCH_URL 이 없다")
    es = pytest.importorskip("elasticsearch")
    c = es.Elasticsearch(url)
    if not c.ping():
        pytest.skip(f"ES 에 붙지 못했다: {url}")
    es_index.create_indices(c, "single", recreate=True)
    es_index.index_chunks(c, load_chunks(KB_ROOT), "single")
    return c


@pytest.mark.integration
def test_색인이_살아있고_알려진_발화가_정답을_1위로_찾는다(client):
    """연기 감지용. 색인이 비었거나 nori 가 빠지면 여기서 걸린다.

    발화는 골든셋 GS-003 원문 그대로다. **검색 품질을 여기서 단언하지 않는다** — 어떤 발화가
    정답을 찾느냐는 평가 하네스가 잴 일이고, 못 찾는 것도 베이스라인의 사실이다.
    실제로 GS-001·GS-019 는 top-5 에 못 든다(2026-08-27 실측, 티켓 참고). 그걸 테스트
    실패로 만들면 "숫자를 좋게 만들려고 테스트를 고치는" 압력이 생긴다.
    """
    utterance = "이거 그냥 마음에 안 들어서 반품하려는데 배송비는 제가 내야 하나요"
    docs = asyncio.run(EsBm25Retriever(client).retrieve(utterance, top_k=5))
    assert [d.doc_id for d in docs][0] == "SHOP-TERM-4.2"


@pytest.mark.integration
def test_점수가_내림차순이다(client):
    docs = asyncio.run(EsBm25Retriever(client).retrieve("환불 기간", top_k=5))
    assert docs, "결과가 비었다"
    assert [d.score for d in docs] == sorted((d.score for d in docs), reverse=True)


@pytest.mark.integration
def test_결과에_중복_조항이_없다(client):
    docs = asyncio.run(EsBm25Retriever(client).retrieve("해지 수수료", top_k=5))
    ids = [d.doc_id for d in docs]
    assert len(ids) == len(set(ids))


@pytest.mark.integration
def test_도메인_필터가_그_도메인만_돌려준다(client):
    """필터를 안 걸면 다른 도메인이 섞인다 — 2026-08-27 실측으로 확인된 실제 현상이다.

    금융 질의(GS-001)의 top-3 에 `DASAN-MANUAL-4.1`·`HLT-MANUAL-1.4` 가 들어왔다.
    B-0 라우팅을 포트에 태우면 이게 줄어든다.
    """
    utterance = "지금 이 시간에 문 연 병원이 근처에 있는지 알 수 있을까요"  # 골든셋 GS-020
    unfiltered = asyncio.run(EsBm25Retriever(client).retrieve(utterance, top_k=5))
    filtered = asyncio.run(EsBm25Retriever(client, domain="health").retrieve(utterance, top_k=5))

    assert filtered, "결과가 비었다"
    assert all(d.doc_id.startswith("HLT-") for d in filtered)
    assert any(not d.doc_id.startswith("HLT-") for d in unfiltered), (
        "필터 없이도 전부 health 라면 이 테스트가 필터를 검증하지 못한다"
    )


# 하네스 배선 테스트(`Ports(retrieval=...)` 에 꽂으면 숫자가 나오는가)는 여기 두지 않는다.
# `retrieval` 이 `evaluation` 을 import 하면 `.importlinter` 의 module-independence 계약이
# 깨진다 — 두 모듈의 접점은 hub 포트(추상)뿐이어야 한다. 배선은 합성 루트의 일이라
# `ai/tests/test_eval_wiring.py` 로 옮겼다(`server/tests/` 가 main.py 에 대해 하는 역할과 같다).
