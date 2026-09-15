# Requirement: B-2
"""하이브리드 검색 — BM25 와 임베딩 순위를 **우리 코드에서** RRF 로 합친다 (`w4-rrf-hybrid`).

ES 의 `rrf` 리트리버를 쓰지 않는다 — basic 라이선스에서 403 이다(`_project/decisions/021`).
병합 산식은 `domain/services/fusion.py` 에 있고, 여기는 두 검색을 부르고 결과를 모양만 바꾼다.

**어느 검색이든 포트(`RetrievalPort`)로 받는다.** BM25·dense 구현을 직접 알 필요가 없고,
리랭커가 이 위에 다시 한 겹 얹힌다(`w4-reranker`).

`k` 는 설정이다 — 60 은 Cormack et al.(2009) 의 관례지 우리 데이터의 측정값이 아니다.
`candidates` 는 병합 전에 각 검색에서 가져올 수다. top_k(5)만 가져오면 한쪽 6등이 다른 쪽
1등이어도 병합 후보에서 빠진다.
"""

from __future__ import annotations

import asyncio
from typing import Sequence

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort

from retrieval.domain.services.fusion import DEFAULT_K, reciprocal_rank_fusion


class HybridRetriever(RetrievalPort):
    def __init__(
        self,
        retrievers: Sequence[RetrievalPort],
        *,
        k: int = DEFAULT_K,
        candidates: int = 20,
        weights: Sequence[float] | None = None,
    ) -> None:
        if len(retrievers) < 2:
            raise ValueError("하이브리드는 검색이 둘 이상이어야 한다")
        self._retrievers = list(retrievers)
        self._k = k
        self._candidates = candidates
        self._weights = list(weights) if weights is not None else None

    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        if not utterance.strip():
            return []
        n = max(self._candidates, top_k)
        # 두 검색을 동시에 부른다 — 순서대로 부르면 지연이 합이 된다(4.1절 p95 ≤1,000ms)
        results = await asyncio.gather(*(r.retrieve(utterance, top_k=n) for r in self._retrievers))

        by_id: dict[str, RetrievedDoc] = {}
        for docs in results:
            for d in docs:
                by_id.setdefault(d.doc_id, d)
        fused = reciprocal_rank_fusion(
            [[d.doc_id for d in docs] for docs in results], k=self._k, weights=self._weights
        )
        return [
            RetrievedDoc(doc_id=i, title=by_id[i].title, snippet=by_id[i].snippet, score=score)
            for i, score in fused[:top_k]
        ]
