# Requirement: B-4, B-5, B-6
"""폴백 생성 — 검색 스니펫을 카드 summary 로 그대로 옮긴다. 모델을 쓰지 않는다.

[7.3절 카드 계약](/docs/07/)이 정한 모드다 —
*"폴백 모드(생성 없이 스니펫 표시)에서도 같은 형태다 — summary 에 원문 스니펫이 들어갈 뿐이다."*

**지어내지 않으므로 환각이 구조적으로 0이다.** generation 스포크(B-4)가 붙기 전까지 이걸 쓰면
검색 품질만 따로 볼 수 있고, 붙은 뒤에는 **환각 건수 비교의 기준선**이 된다.

`source` 가 없는 문서는 카드로 만들지 않는다 — 출처 없는 카드를 렌더링하지 않는다(B-5·B-6).
"""

from __future__ import annotations

from hub.app.dtos.recommendation_card_dto import Card, Source
from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.generation_port import GenerationPort


class SnippetCardAdapter(GenerationPort):
    async def to_cards(self, utterance: str, docs: list[RetrievedDoc]) -> list[Card]:
        return [
            Card(
                title=doc.title,
                summary=doc.snippet,  # 그대로 옮긴다 — 요약하지 않으므로 없는 말이 섞일 수 없다
                source=Source(doc_id=doc.doc_id, title=doc.title),
                similarity_score=doc.score,
            )
            for doc in docs
            if doc.doc_id  # 출처 없는 문서는 카드가 되지 않는다 (B-6)
        ]
