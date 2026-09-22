# Requirement: B-2
"""BM25 검색 어댑터 (w2-naive-rag).

ES 없이 도는 절반은 **가짜 클라이언트**로 질의 모양과 응답 변환을 고정한다. CI 가 이걸 돌린다.
`@pytest.mark.integration` 은 실제 ES 가 있을 때만 돈다. **공유 인덱스(`callguard-kb-single`)를
건드리지 않는다** — 모듈마다 `callguard-test-<uuid>` 접두어의 임시 인덱스를 만들어 지식베이스를
BM25 로 적재하고, 끝나면 지운다(2026-09-22, `w6-test-hygiene-eval-wiring`). 전에는 여기서 공유
인덱스를 `recreate=True` 로 다시 만들어 **개발 인덱스의 dense 벡터를 조용히 0건으로** 만들었다.
"""

from __future__ import annotations

import asyncio
import os
import uuid
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

# 임시 인덱스 접두어. `callguard-kb-` 로 시작하지 않게 한다 — 운영 레이아웃 와일드카드
# (`callguard-kb-*`)에 섞이지 않도록(`es_index.create_named_index` 가 실험 인덱스에 거는 것과 같은 규칙).
TEST_PREFIX_HEAD = "callguard-test-"


@pytest.fixture(scope="module")
def es():
    url = os.environ.get("ELASTICSEARCH_URL")
    if not url:
        pytest.skip("ELASTICSEARCH_URL 이 없다")
    elasticsearch = pytest.importorskip("elasticsearch")
    c = elasticsearch.Elasticsearch(url)
    if not c.ping():
        pytest.skip(f"ES 에 붙지 못했다: {url}")
    return c


@pytest.fixture(scope="module")
def temp_index(es):
    """이 모듈만 쓰는 임시 인덱스. 끝나면 지운다 — 실패해도 teardown 은 돈다."""
    prefix = f"{TEST_PREFIX_HEAD}{uuid.uuid4().hex[:12]}"
    (name,) = es_index.index_names("single", prefix=prefix)
    assert name != es_index.SINGLE_INDEX and not name.startswith(es_index.INDEX_PREFIX + "-")
    print(f"\n[integration] 임시 인덱스: {name}")
    try:
        es_index.create_indices(es, "single", prefix=prefix)
        es_index.index_chunks(es, load_chunks(KB_ROOT), "single", prefix=prefix)
        yield name
    finally:
        es.indices.delete(index=name, ignore_unavailable=True)


@pytest.fixture(scope="module")
def client(es, temp_index):
    return es


def _retriever(client, temp_index, **kwargs):
    return EsBm25Retriever(client, index=temp_index, **kwargs)


@pytest.mark.integration
def test_색인이_살아있고_알려진_발화가_정답을_1위로_찾는다(client, temp_index):
    """연기 감지용. 색인이 비었거나 nori 가 빠지면 여기서 걸린다.

    발화는 골든셋 GS-259 원문 그대로다(정답 `DASAN-TERM-4.15` 「신혼부부 특별공급」).
    2026-09-22 실측에서 1위 점수가 2위의 **4.37배**로 골든셋 B 항목 중 격차가 가장 컸다 —
    조항이 몇 개 늘어도 뒤집히지 않을 만큼 벌어진 것을 골랐다. 전에는 GS-003 의
    `SHOP-TERM-4.2` 를 기대했는데, 쇼핑 도메인이 2026-08-28 삭제돼(`decisions/201`) 늘 실패했다.

    **검색 품질을 여기서 단언하지 않는다** — 어떤 발화가 정답을 찾느냐는 평가 하네스가 잴 일이고,
    못 찾는 것도 베이스라인의 사실이다. 그걸 테스트 실패로 만들면 "숫자를 좋게 만들려고 테스트를
    고치는" 압력이 생긴다. 여기서 보는 것은 «색인·분석기·질의가 이어져 있는가» 하나다.
    """
    utterance = "신혼부부 특별공급 자격이 어떻게 되나요"
    docs = asyncio.run(_retriever(client, temp_index).retrieve(utterance, top_k=5))
    assert docs, "결과가 비었다 — 색인이 비었거나 분석기가 빠졌다"
    assert docs[0].doc_id == "DASAN-TERM-4.15", [d.doc_id for d in docs]


@pytest.mark.integration
def test_점수가_내림차순이다(client, temp_index):
    docs = asyncio.run(_retriever(client, temp_index).retrieve("환불 기간", top_k=5))
    assert docs, "결과가 비었다"
    assert [d.score for d in docs] == sorted((d.score for d in docs), reverse=True)


@pytest.mark.integration
def test_결과에_중복_조항이_없다(client, temp_index):
    docs = asyncio.run(_retriever(client, temp_index).retrieve("해지 수수료", top_k=5))
    ids = [d.doc_id for d in docs]
    assert len(ids) == len(set(ids))


@pytest.mark.integration
def test_도메인_필터가_실제로_질의에_걸린다(client, temp_index):
    """지식베이스가 다산 하나라(`decisions/201`) «다른 도메인이 섞이는가» 는 더 볼 수 없다.
    대신 필터가 **ES 질의에 실제로 먹는지**를 양쪽에서 본다 —

    - `dasan` 으로 좁히면 필터 없는 결과와 같다(전부 다산이므로). 필터가 결과를 망가뜨리지 않는다.
    - 색인에 없는 도메인(`finance` — 08-28 삭제)으로 좁히면 **0건**이다. 필터가 무시되고 있다면
      여기서 필터 없는 결과가 그대로 나온다 — 첫 단언만으로는 이 둘을 구분할 수 없다.

    전에는 GS-020(병원) 을 `health` 로 좁혀 `HLT-` 만 나오는지 봤는데, 그 도메인이 삭제돼 늘 실패했다.
    """
    utterance = "장애인콜택시 등록하려면 뭘 준비해야 하나요"  # 골든셋 GS-209
    unfiltered = asyncio.run(_retriever(client, temp_index).retrieve(utterance, top_k=5))
    dasan = asyncio.run(_retriever(client, temp_index, domain="dasan").retrieve(utterance, top_k=5))
    absent = asyncio.run(_retriever(client, temp_index, domain="finance").retrieve(utterance, top_k=5))

    assert unfiltered, "필터 없이도 결과가 비었다 — 이 테스트가 필터를 검증하지 못한다"
    assert all(d.doc_id.startswith("DASAN-") for d in dasan)
    assert [d.doc_id for d in dasan] == [d.doc_id for d in unfiltered]
    assert absent == [], f"색인에 없는 도메인으로 좁혔는데 결과가 나왔다 — 필터가 안 걸린다: {absent}"


# 하네스 배선 테스트(`Ports(retrieval=...)` 에 꽂으면 숫자가 나오는가)는 여기 두지 않는다.
# `retrieval` 이 `evaluation` 을 import 하면 `.importlinter` 의 module-independence 계약이
# 깨진다 — 두 모듈의 접점은 hub 포트(추상)뿐이어야 한다. 배선은 합성 루트의 일이라
# `ai/tests/test_eval_wiring.py` 로 옮겼다(`server/tests/` 가 main.py 에 대해 하는 역할과 같다).
