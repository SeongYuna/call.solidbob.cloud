# Requirement: B-2
"""앞 검색이 **0건이면** 뒤 검색으로 내려간다.

임베딩 검색은 인덱스에 벡터가 없으면 오류 없이 0건을 돌려준다(`scripts/index_knowledge_base.py` 가
torch 없는 곳에서 BM25 만 적재한 경우 — 운영 서버 파드가 그렇다, 런북 15-1). 그 상태로 dense 를 꽂으면
**모든 추천이 「관련 문서 없음」이 된다** — 조용히. 그래서 0건일 때만 BM25 로 내려간다.

⚠ 0건이 아닌 «나쁜 결과» 는 구분하지 않는다. 그건 품질 문제라 하네스가 잰다.
"""

from __future__ import annotations

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort


class FallbackRetriever(RetrievalPort):
    def __init__(self, primary: RetrievalPort, fallback: RetrievalPort) -> None:
        self._primary = primary
        self._fallback = fallback
        self.fallbacks = 0  # 내려간 횟수 — 0 이 아니면 인덱스에 벡터가 없는지 본다

    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        if not utterance.strip():
            return []
        docs = await self._primary.retrieve(utterance, top_k=top_k)
        if docs:
            return docs
        self.fallbacks += 1
        return await self._fallback.retrieve(utterance, top_k=top_k)
