# Requirement: B-2
"""BM25 검색 — `RetrievalPort` 의 첫 구현체 (w2-naive-rag).

발화 → 조항 목록. **리랭킹·생성·하이브리드 없이 검색만** 한다. 계약(포트·DTO)은 `server/` 가
정의하고 여기서 구현한다 — 의존 방향은 `ai → server` 한쪽뿐이다.

ES 를 부르므로 adapter 계층이다. 색인은 `es_index.py`, 여기는 읽기만 한다.

## 왜 이렇게 단순한가

4주차에 dense_vector·리랭킹을 넣고 **개선 폭을 수치로** 보여주기 위해서다. 처음부터 다 넣으면
무엇이 얼마나 기여했는지 말할 수 없다([평가 설계](/docs/06/)). 그래서 여기서는 필드 가중치도
주지 않는다 — `title^2` 같은 튜닝은 4주차에 붙이고 그 차이를 잰다.

## 남아 있는 것 두 가지 (이 티켓 범위 밖)

1. **도메인 필터를 쓰지 않는다.** `RetrievalPort.retrieve(utterance, top_k)` 시그니처에
   도메인이 없어서 하네스가 넘겨줄 방법이 없다. 지금은 4개 도메인 전체를 검색한다.
   B-0 라우팅을 실제로 태우려면 포트 시그니처를 바꿔야 하고, 그건 `server/` 소관이다.
   생성자의 `domain=` 은 그때까지 쓰는 임시 통로다(하네스는 쓰지 않는다).
2. **nori 가 이미 베이스라인에 들어 있다.** `w2-kb-index` 티켓은 "2주차는 nori 없이"라고
   적었지만 색인 매핑이 이미 nori 다. 8주 로드맵의 "4주차 nori 인덱스"로는 개선 폭을 못 잰다 —
   재려면 `standard` 애널라이저 인덱스를 따로 적재해 비교해야 한다(재적재가 1초라 언제든 된다).
   [미결 항목](/open-items/) 참고.
"""

from __future__ import annotations

import asyncio
from typing import Any

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort

from retrieval.adapter.outbound.es_index import SINGLE_INDEX
from retrieval.domain.value_objects.chunk import NON_RECOMMENDABLE_DOC_TYPES

# BM25 가 훑을 필드. 가중치를 주지 않는다 — 위 "왜 이렇게 단순한가" 참고.
SEARCH_FIELDS = ("title", "text")


class EsBm25Retriever(RetrievalPort):
    """Elasticsearch BM25(nori) 단독 검색.

    client 는 주입받는다. 합성은 `scripts/run_eval.py` 가 한다 — `evaluation` 이 `retrieval`
    을 직접 import 하면 `.importlinter` 의 module-independence 계약이 깨진다.
    """

    def __init__(
        self,
        client: Any,
        *,
        index: str = SINGLE_INDEX,
        domain: str | None = None,
    ) -> None:
        self._client = client
        self._index = index
        self._domain = domain

    def build_query(self, utterance: str) -> dict[str, Any]:
        """발화 → ES 질의. 질의 모양만 따로 떼어 테스트에서 ES 없이 확인한다."""
        match: dict[str, Any] = {
            "multi_match": {"query": utterance, "fields": list(SEARCH_FIELDS)}
        }
        # must_not·filter 절은 점수에 영향을 주지 않는다 — 후보를 좁힐 뿐 순위를 바꾸지 않는다.
        query: dict[str, Any] = {
            "must": [match],
            "must_not": [{"terms": {"doc_type": list(NON_RECOMMENDABLE_DOC_TYPES)}}],
        }
        if self._domain is not None:
            query["filter"] = [{"term": {"domain": self._domain}}]
        return {"bool": query}

    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        """상위 top_k 조항. 빈 발화면 검색하지 않는다.

        빈 결과를 억지로 채우지 않는다 — 근거가 없으면 "관련 문서 없음"이 맞다(B-6).
        """
        if not utterance.strip():
            return []

        # 동기 클라이언트를 이벤트 루프 밖에서 돌린다. 서버가 이 어댑터를 실제 요청 경로에
        # 물릴 때는 AsyncElasticsearch 로 바꾸는 편이 낫다 — 지금은 하네스가 유일한 소비자다.
        resp = await asyncio.to_thread(
            self._client.search,
            index=self._index,
            query=self.build_query(utterance),
            size=top_k,
            # 조항 하나가 상한을 넘어 여러 청크로 쪼개졌을 때, 그 청크들이 top_k 자리를
            # 나눠 먹지 않게 한다. 채점 단위가 doc_id 이므로 같은 조항이 두 칸을 차지하면
            # Recall@5 의 유효 후보가 줄어든다. 지금은 분할이 0건이라 동작 차이가 없지만,
            # 지식베이스가 길어지면 조용히 손해가 나는 자리다.
            collapse={"field": "doc_id"},
        )
        return [self._to_doc(hit) for hit in resp["hits"]["hits"]]

    @staticmethod
    def _to_doc(hit: dict[str, Any]) -> RetrievedDoc:
        """검색 결과 1건 → 계약 DTO.

        `doc_id` 는 `_id`(= chunk_id) 가 아니라 **본문의 doc_id** 를 쓴다. 조항이 상한을 넘어
        쪼개지면 `_id` 에 `#1` 이 붙는데, 골든셋 `expected_doc_ids` 는 조항 ID 단위라
        `_id` 를 그대로 쓰면 채점이 어긋난다(`collapse` 도 같은 이유로 `doc_id` 기준이다).
        """
        src = hit["_source"]
        return RetrievedDoc(
            doc_id=src["doc_id"],
            title=src["title"],
            snippet=src["text"],
            score=hit["_score"],
        )
