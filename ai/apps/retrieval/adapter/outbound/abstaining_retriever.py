# Requirement: B-6, B-2
"""**수동 검색 전용** 기권 — 1순위가 문턱 아래면 「관련 문서 없음」을 돌려준다(`_project/decisions/135`).

`FallbackRetriever(abstain_below=...)` 와 규칙은 같지만 **걸리는 자리가 다르다.** 저쪽은 자동 추천
(대화 중 트리거가 발동한 검색)까지 함께 걸려서 `decisions/215` 가 보류했다 — 대화체 발화의 dense
1순위가 0.60~0.67 에 몰려 발동 추천의 60%(114/189)가 기권했고 필요서류 절차가 사라졌다.

**여기는 상담원이 직접 친 질의만 지난다**(`POST /hub/search` — 「관련 문서를 못 찾으셨나요?」).
맞장구·잡담이 들어오지 않고, 기권해도 사라지는 자동 카드가 없다. 문턱 값을 잰 보류 표본
(`golden-set/b6-holdout-2026-09-22.json` 24건)이 바로 **이 모양의 질의**다 — 「…어디로 가야 되나요」.

⚠ 문턱은 dense 코사인 눈금(`(1+cos)/2`)에 묶인다 — 리랭커(로짓)·BM25(raw)가 1순위를 정하는 구성에는
씌우지 않는다. 씌울지 고르는 곳은 `ai/provider.py` 의 `wrap_no_answer()` 다.
"""

from __future__ import annotations

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort


class AbstainingRetriever(RetrievalPort):
    def __init__(self, inner: RetrievalPort, *, min_score: float) -> None:
        self._inner = inner
        self._min_score = min_score
        self.abstentions = 0  # 기권 횟수 — 「관련 문서 없음」이 된 수동 검색 수

    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        docs = await self._inner.retrieve(utterance, top_k=top_k)
        if docs and max(d.score for d in docs) < self._min_score:
            self.abstentions += 1
            return []
        return docs
