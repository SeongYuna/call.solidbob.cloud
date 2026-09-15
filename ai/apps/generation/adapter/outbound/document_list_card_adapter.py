# Requirement: B-4, B-5, B-6
"""`GenerationPort` 구현 — 상위 조항에서 **서류 목록 카드**를 만든다 (`w6-card-generation`).

    검색 결과 ─┬─ 상위 N 건: 모델이 서류 이름을 고름 → 규칙 검사(근거 대조·금지 표현) → "필요 서류: A · B"
               │     └─ 남는 항목 0 · 모델 「없음」 · 타임아웃 · 오류 → 스니펫 카드로 내려감
               └─ 나머지: 스니펫 카드 (폴백, `server` 의 `SnippetCardAdapter` 와 같은 모양)

**출처 없는 카드는 만들지 않는다**(B-5) — `doc_id` 가 없으면 건너뛴다. **문서가 0건이면 빈 목록**(B-6 「관련 문서 없음」).
**어느 조항이 정답인지는 검색이 정했다** — 여기서는 순서도 바꾸지 않고 조항을 고르지도 않는다(절대 원칙 9).

**상위 N 건만 생성하는 이유**: Ollama 는 `NUM_PARALLEL=1`(런북 14-1)이라 조항 수만큼 순서대로 기다린다.
상담원은 맨 위 카드부터 읽고(MRR), 4.3절 예산은 트리거 → 카드 표시 p95 ≤1,000ms 다. 기본 1건 — 지연을 재고 늘린다.

`last_details` 에 조항별 원출력·검사 결과를 남긴다 — 환각 채점(`w6-hallucination-eval`)과 토큰 측정(`w7-token-cost`)이 쓴다.
**원출력은 화면에 나가지 않는다.**
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Protocol

from hub.app.dtos.recommendation_card_dto import Card, Source
from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.generation_port import GenerationPort

from ...domain.services.document_list import (
    DOCUMENTS_SCHEMA,
    ItemCheck,
    build_messages,
    check_items,
    compose_summary,
    is_none_answer,
    parse_items,
)

log = logging.getLogger(__name__)


class ChatClient(Protocol):
    model: str

    def chat(self, messages: list[dict[str, str]], *, schema: dict | None = None): ...


@dataclass(frozen=True)
class GenerationDetail:
    doc_id: str
    outcome: str  # "generated" | "none" | "no_grounded_items" | "error"
    raw_output: str
    check: ItemCheck | None
    prompt_tokens: int = 0
    output_tokens: int = 0
    elapsed_ms: float = 0.0


def _snippet_card(doc: RetrievedDoc) -> Card:
    return Card(title=doc.title, summary=doc.snippet, source=Source(doc_id=doc.doc_id, title=doc.title), similarity_score=doc.score)


class DocumentListCardAdapter(GenerationPort):
    def __init__(self, chat: ChatClient, *, generate_top_n: int = 1, use_schema: bool = True) -> None:
        # use_schema=False 는 모델 대조용이다 — 대조군 kanana 는 Ollama 0.33.3 에서 JSON 스키마 강제가 500 을 낸다(2026-09-15)
        self._chat = chat
        self._top_n = generate_top_n
        self._schema = DOCUMENTS_SCHEMA if use_schema else None
        self.last_details: list[GenerationDetail] = []

    async def to_cards(self, utterance: str, docs: list[RetrievedDoc]) -> list[Card]:
        cards: list[Card] = []
        details: list[GenerationDetail] = []
        for i, doc in enumerate(d for d in docs if d.doc_id):
            if i >= self._top_n:
                cards.append(_snippet_card(doc))
                continue
            card, detail = await asyncio.to_thread(self._generate_one, utterance, doc)
            cards.append(card)
            details.append(detail)
        self.last_details = details
        return cards

    def _generate_one(self, utterance: str, doc: RetrievedDoc) -> tuple[Card, GenerationDetail]:
        try:
            res = self._chat.chat(build_messages(utterance, doc.title, doc.snippet), schema=self._schema)
        except Exception as e:  # noqa: BLE001 — 생성이 죽어도 스니펫 카드는 나간다
            log.warning("생성 실패 — 스니펫 카드로: %s", type(e).__name__)
            return _snippet_card(doc), GenerationDetail(doc.doc_id, "error", "", None)

        meta = dict(prompt_tokens=res.prompt_tokens, output_tokens=res.output_tokens, elapsed_ms=res.elapsed_ms)
        if is_none_answer(res.content):
            return _snippet_card(doc), GenerationDetail(doc.doc_id, "none", res.content, None, **meta)

        # 근거 대조는 **본문만** 본다. 제목까지 넣었더니 「3.15 옥내 배관 문의」 같은 조항 제목이 서류 이름으로 통과했다(2026-09-15)
        check = check_items(parse_items(res.content), doc.snippet)
        if not check.grounded:
            return _snippet_card(doc), GenerationDetail(doc.doc_id, "no_grounded_items", res.content, check, **meta)
        card = Card(
            title=doc.title,
            summary=compose_summary(check.grounded),
            source=Source(doc_id=doc.doc_id, title=doc.title),
            similarity_score=doc.score,
        )
        return card, GenerationDetail(doc.doc_id, "generated", res.content, check, **meta)
