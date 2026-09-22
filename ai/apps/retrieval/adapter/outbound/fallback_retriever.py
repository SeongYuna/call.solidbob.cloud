# Requirement: B-2, B-6
"""앞 검색이 **0건이면** 뒤 검색으로 내려간다. 앞 검색이 냈지만 1순위가 문턱 아래면 **기권**한다(B-6).

임베딩 검색은 인덱스에 벡터가 없으면 오류 없이 0건을 돌려준다(`scripts/index_knowledge_base.py` 가
torch 없는 곳에서 BM25 만 적재한 경우 — 운영 서버 파드가 그렇다, 런북 15-1). 그 상태로 dense 를 꽂으면
**모든 추천이 「관련 문서 없음」이 된다** — 조용히. 그래서 0건일 때만 BM25 로 내려간다.

**B-6 기권(`abstain_below`, `_project/decisions/215`)** — 앞 검색이 문서를 냈는데 1순위 점수가 문턱 아래면
빈 결과를 돌려주고 **BM25 로 내려가지 않는다.** 내려가면 BM25 가 카드 5장을 다시 채워 문턱이 아무 일도
안 한다(운영 SYN-010 에서 「감사합니다」에 무관한 조항 5장이 뜬 그 상태로 돌아간다). 두 경우를 가르는 것은
«0건» 이다 — 0건은 벡터가 없다는 뜻이라 내려가고, 1건 이상은 검색이 돌았다는 뜻이라 점수를 본다.

⚠ 문턱 값은 **앞 검색의 점수 눈금**에 묶인다 — dense 코사인(`(1+cos)/2`)으로 잰 값이라 리랭커(로짓)나
BM25(raw)가 앞에 서면 의미가 없다. 그래서 값을 여기 두지 않고 조립하는 쪽(`ai/provider.py`)이 dense 단독일
때만 넘긴다. None 이면 기권하지 않는다(오늘까지의 동작).

⚠ 0건이 아닌 «나쁜 결과» 를 문턱 밖에서 구분하지는 않는다. 그건 품질 문제라 하네스가 잰다.
"""

from __future__ import annotations

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort


class FallbackRetriever(RetrievalPort):
    def __init__(
        self,
        primary: RetrievalPort,
        fallback: RetrievalPort,
        *,
        abstain_below: float | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._abstain_below = abstain_below
        self.fallbacks = 0  # 내려간 횟수 — 0 이 아니면 인덱스에 벡터가 없는지 본다
        self.abstentions = 0  # 문턱으로 기권한 횟수 — 「관련 문서 없음」이 된 추천 수(B-6)

    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        if not utterance.strip():
            return []
        docs = await self._primary.retrieve(utterance, top_k=top_k)
        if docs:
            if self._abstain_below is not None and max(d.score for d in docs) < self._abstain_below:
                self.abstentions += 1
                return []  # 기권 — 뒤 검색으로 내려가지 않는다(decisions/215)
            return docs
        self.fallbacks += 1
        return await self._fallback.retrieve(utterance, top_k=top_k)
