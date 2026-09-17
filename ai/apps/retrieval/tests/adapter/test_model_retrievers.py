# Requirement: B-2, B-3
"""임베딩·하이브리드·리랭킹·폴백 검색 — 모델·ES 없이 가짜 포트로 **배선과 불변식**만 고정한다.

실제 수치는 `scripts/compare_retrievers.py` 가 낸다(`w4-dense-vector-index` · `w4-rrf-hybrid` · `w4-reranker`).
"""

from __future__ import annotations

import asyncio

import pytest

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort

from retrieval.adapter.outbound import es_index
from retrieval.adapter.outbound.cross_encoder_reranker import CrossEncoderReranker
from retrieval.adapter.outbound.es_dense_retriever import EsDenseRetriever
from retrieval.adapter.outbound.fallback_retriever import FallbackRetriever
from retrieval.adapter.outbound.hybrid_retriever import HybridRetriever
from retrieval.domain.services.rerank import reorder
from retrieval.domain.value_objects.chunk import Chunk


def doc(i: str, score: float = 1.0) -> RetrievedDoc:
    return RetrievedDoc(doc_id=i, title=f"t{i}", snippet=f"s{i}", score=score)


class Fixed(RetrievalPort):
    def __init__(self, ids: list[str]):
        self.ids = ids
        self.asked: list[int] = []

    async def retrieve(self, utterance, top_k=5):
        self.asked.append(top_k)
        return [doc(i) for i in self.ids[:top_k]]


def run(coro):
    return asyncio.run(coro)


class TestDense:
    class Client:
        def __init__(self):
            self.calls = []

        def search(self, **kw):
            self.calls.append(kw)
            return {"hits": {"hits": [{"_score": 0.9, "_source": {"doc_id": "D-1", "title": "제목", "text": "본문"}}]}}

    class Embedder:
        def __init__(self):
            self.seen = []

        def embed_queries(self, texts):
            self.seen.extend(texts)
            return [[0.1] * 4 for _ in texts]

    def test_knn_query_shape_and_mapping(self):
        client, emb = self.Client(), self.Embedder()
        docs = run(EsDenseRetriever(client, emb, index="ix", num_candidates=100).retrieve("등본 서류", top_k=5))
        call = client.calls[0]
        assert call["knn"]["field"] == es_index.EMBEDDING_FIELD
        assert call["knn"]["k"] == 5 and call["knn"]["num_candidates"] == 100
        assert call["collapse"] == {"field": "doc_id"}  # 채점 단위가 조항이다
        # BM25 와 같이 내부 규정 조항은 후보에서 뺀다(2026-09-17) — dense 로 바꿔도 1순위에 올라오지 않게
        assert call["knn"]["filter"] == {"bool": {"must_not": [{"terms": {"doc_type": ["POLICY"]}}]}}
        assert es_index.EMBEDDING_FIELD in call["source_excludes"]
        assert emb.seen == ["등본 서류"]  # 접두어는 임베더가 붙인다 — 어댑터가 두 번 붙이지 않는다
        assert docs == [RetrievedDoc(doc_id="D-1", title="제목", snippet="본문", score=0.9)]

    def test_empty_utterance_does_not_embed(self):
        client, emb = self.Client(), self.Embedder()
        assert run(EsDenseRetriever(client, emb).retrieve("  ")) == []
        assert emb.seen == [] and client.calls == []


class TestHybrid:
    def test_asks_candidates_not_top_k(self):
        a, b = Fixed(list("ABCDEFG")), Fixed(list("GFEDCBA"))
        run(HybridRetriever([a, b], candidates=20).retrieve("q", top_k=5))
        assert a.asked == [20] and b.asked == [20]

    def test_rrf_order_and_scores(self):
        # A: 1등·7등 / G: 7등·1등 / D: 4등·4등 — k=1 이면 1/(1+1)+1/(1+7)=0.625 vs 2/(1+4)=0.4
        docs = run(HybridRetriever([Fixed(list("ABCDEFG")), Fixed(list("GFEDCBA"))], k=1).retrieve("q", top_k=3))
        assert [d.doc_id for d in docs] == ["A", "G", "B"]
        assert docs[0].score == pytest.approx(1 / 2 + 1 / 8)

    def test_needs_two(self):
        with pytest.raises(ValueError):
            HybridRetriever([Fixed(["A"])])


class TestRerank:
    class ReverseScorer:
        model_name = "fake"

        def __init__(self):
            self.passages = []

        def score(self, query, passages):
            self.passages = list(passages)
            return [float(i) for i in range(len(passages))]  # 뒤에 있을수록 높다

    def test_same_candidates_keep_recall_set(self):
        # candidates == top_k 면 같은 5건을 다시 세울 뿐이다 — 집합이 바뀌면 버그다(티켓 완료 조건)
        inner = Fixed(list("ABCDEFGH"))
        docs = run(CrossEncoderReranker(inner, self.ReverseScorer(), candidates=5).retrieve("q", top_k=5))
        assert {d.doc_id for d in docs} == set("ABCDE")
        assert [d.doc_id for d in docs] == list("EDCBA")

    def test_wider_candidates_can_promote(self):
        docs = run(CrossEncoderReranker(Fixed(list("ABCDEFGH")), self.ReverseScorer(), candidates=8).retrieve("q", top_k=3))
        assert [d.doc_id for d in docs] == list("HGF")

    def test_scorer_sees_title_and_snippet(self):
        scorer = self.ReverseScorer()
        run(CrossEncoderReranker(Fixed(["A"]), scorer, candidates=5).retrieve("q"))
        assert scorer.passages == ["tA\nsA"]

    def test_reorder_is_stable_on_ties(self):
        assert [x for x, _ in reorder(list("ABC"), [1.0, 2.0, 1.0])] == ["B", "A", "C"]

    def test_reorder_length_mismatch(self):
        with pytest.raises(ValueError):
            reorder(["A"], [1.0, 2.0])


class TestFallback:
    def test_uses_primary_when_it_has_results(self):
        fb = FallbackRetriever(Fixed(["A"]), Fixed(["B"]))
        assert [d.doc_id for d in run(fb.retrieve("q"))] == ["A"] and fb.fallbacks == 0

    def test_falls_back_on_empty(self):
        # 벡터 없이 적재된 인덱스 — kNN 은 오류 없이 0건이다
        fb = FallbackRetriever(Fixed([]), Fixed(["B"]))
        assert [d.doc_id for d in run(fb.retrieve("q"))] == ["B"] and fb.fallbacks == 1


class TestIndexEmbedding:
    CHUNK = Chunk(chunk_id="D-1", doc_id="D-1", domain="dasan", doc_type="TERM", title="제목", text="본문")

    def test_mapping_without_dims_has_no_vector(self):
        assert es_index.EMBEDDING_FIELD not in es_index.build_mapping()["properties"]

    def test_mapping_with_dims(self):
        field = es_index.build_mapping(embedding_dims=1024)["properties"][es_index.EMBEDDING_FIELD]
        assert field == {"type": "dense_vector", "dims": 1024, "index": True, "similarity": "cosine"}

    def test_embedding_input_includes_title(self):
        assert es_index.embedding_input(self.CHUNK) == "제목\n본문"

    def test_index_chunks_rejects_partial_embeddings(self):
        class Client:
            def bulk(self, **kw):
                raise AssertionError("부분 임베딩이면 적재하기 전에 멈춰야 한다")

        other = Chunk(chunk_id="D-2", doc_id="D-2", domain="dasan", doc_type="TERM", title="t", text="x")
        with pytest.raises(ValueError, match="임베딩이 없는 청크 1건"):
            es_index.index_chunks(Client(), [self.CHUNK, other], "single", embeddings={"D-1": [0.1]})

    def test_source_carries_vector(self):
        assert es_index.to_source(self.CHUNK, [0.5])[es_index.EMBEDDING_FIELD] == [0.5]
        assert es_index.EMBEDDING_FIELD not in es_index.to_source(self.CHUNK)
