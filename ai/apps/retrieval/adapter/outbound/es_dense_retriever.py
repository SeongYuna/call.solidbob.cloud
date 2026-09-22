# Requirement: B-2, B-6
"""임베딩(kNN) 단독 검색 — `RetrievalPort` 구현 (`w4-dense-vector-index`).

`EsBm25Retriever` 와 **같은 인덱스·같은 반환 형태**다. 둘을 나란히 재야 하이브리드에서
«무엇이 기여했는가» 를 읽을 수 있다(`w4-rrf-hybrid`).

벡터는 `scripts/index_knowledge_base.py --to-es` 가 본문과 함께 넣는다. **벡터 없이 적재된
인덱스에서는 결과가 0건이다** — 오류가 아니라 후보가 없는 것이라, 그 상태로 재면 Recall 이 0 으로 나온다.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, Sequence

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort

from retrieval.adapter.outbound.es_index import EMBEDDING_FIELD, SINGLE_INDEX
from retrieval.domain.value_objects.chunk import NON_RECOMMENDABLE_DOC_TYPES


# B-6 「관련 문서 없음」 문턱 — 이 검색의 1순위 `_score`(ES cosine `(1+cos)/2`, 0~1)가 이 값보다 낮으면 기권한다.
# `_project/decisions/215`: 후보를 먼저 얼리고(0.67) 고르는 데 안 쓴 정답 없음 24건(`golden-set/b6-holdout-2026-09-22.json`)
# 으로 한 번 쟀다 — 걸러냄 12/24 · 정답 손실 1/93(GS-218). **이 눈금에만 맞는 값이다** — 리랭커 로짓·BM25 raw 에 쓰지 않는다.
# 적용은 `FallbackRetriever(abstain_below=...)` 가 하고, 넘기는 곳은 `ai/provider.py` 다(dense 단독일 때만).
NO_ANSWER_MIN_SCORE = 0.67


class QueryEmbedder(Protocol):
    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]: ...


class EsDenseRetriever(RetrievalPort):
    def __init__(
        self,
        client: Any,
        embedder: QueryEmbedder,
        *,
        index: str = SINGLE_INDEX,
        num_candidates: int = 100,
    ) -> None:
        # num_candidates 는 HNSW 가 샤드에서 훑는 후보 수다. 조항이 98개라 100 이면 사실상 전수 비교다 —
        # 근사 오차를 비교에서 빼기 위해서다. 지식베이스가 수천 건이 되면 지연을 보고 다시 정한다.
        self._client = client
        self._embedder = embedder
        self._index = index
        self._num_candidates = num_candidates

    def build_knn(self, vector: list[float], top_k: int) -> dict[str, Any]:
        return {
            "field": EMBEDDING_FIELD,
            "query_vector": vector,
            "k": top_k,
            "num_candidates": max(self._num_candidates, top_k),
            # BM25 와 같은 후보 제외(내부 규정 조항) — knn 의 filter 는 근사 탐색 **전에** 걸려 k 개를 온전히 채운다
            "filter": {"bool": {"must_not": [{"terms": {"doc_type": list(NON_RECOMMENDABLE_DOC_TYPES)}}]}},
        }

    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        if not utterance.strip():
            return []
        vector = (await asyncio.to_thread(self._embedder.embed_queries, [utterance]))[0]
        resp = await asyncio.to_thread(
            self._client.search,
            index=self._index,
            knn=self.build_knn(vector, top_k),
            size=top_k,
            collapse={"field": "doc_id"},  # BM25 와 같은 이유 — 채점 단위가 조항이다
            source_excludes=[EMBEDDING_FIELD],  # 1024차원을 매번 돌려받지 않는다
        )
        return [
            RetrievedDoc(
                doc_id=h["_source"]["doc_id"],
                title=h["_source"]["title"],
                snippet=h["_source"]["text"],
                score=h["_score"],
            )
            for h in resp["hits"]["hits"]
        ]
