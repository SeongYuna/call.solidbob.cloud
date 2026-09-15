# Requirement: B-4, B-5, B-6
"""카드 어댑터 — 가짜 채팅 클라이언트로 폴백·출처·상위 N 규칙을 고정한다. 실제 모델 수치는 `scripts/eval_generation.py`."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc

from generation.adapter.outbound.document_list_card_adapter import DocumentListCardAdapter


@dataclass
class Res:
    content: str
    prompt_tokens: int = 10
    output_tokens: int = 5
    elapsed_ms: float = 1.0


class Chat:
    model = "fake"

    def __init__(self, content="- 위임장\n- 가족관계증명서", fail=False):
        self.content, self.fail, self.calls = content, fail, 0

    def chat(self, messages, schema=None):
        self.schema = schema
        self.calls += 1
        if self.fail:
            raise TimeoutError("느림")
        return Res(self.content)


DOC = RetrievedDoc(doc_id="DASAN-TERM-4.3", title="4.3 초본 — 필요서류", snippet="대리 발급은 위임장과 대리인 신분증이 필요하다.", score=0.9)
DOC2 = RetrievedDoc(doc_id="DASAN-TERM-2.1", title="2.1 버스", snippet="실시간 배차 안내", score=0.5)


def run(adapter, docs):
    return asyncio.run(adapter.to_cards("초본 대리 발급 서류요", docs))


def test_grounded_items_only_and_hallucination_counted():
    adapter = DocumentListCardAdapter(Chat())
    (card, snippet) = run(adapter, [DOC, DOC2])
    assert card.summary == "필요 서류: 위임장"  # 조항에 없는 가족관계증명서는 버렸다
    assert card.source.doc_id == "DASAN-TERM-4.3" and card.similarity_score == 0.9
    assert snippet.summary == DOC2.snippet  # 상위 1건만 생성
    (detail,) = adapter.last_details
    assert detail.outcome == "generated" and detail.check.hallucinated == 1


def test_only_top_n_calls_model():
    chat = Chat()
    run(DocumentListCardAdapter(chat, generate_top_n=1), [DOC, DOC2, DOC])
    assert chat.calls == 1


def test_none_answer_falls_back_to_snippet():
    adapter = DocumentListCardAdapter(Chat(content="없음"))
    (card,) = run(adapter, [DOC])
    assert card.summary == DOC.snippet and adapter.last_details[0].outcome == "none"


def test_all_items_ungrounded_falls_back_to_snippet():
    adapter = DocumentListCardAdapter(Chat(content="- 가족관계증명서"))
    (card,) = run(adapter, [DOC])
    assert card.summary == DOC.snippet and adapter.last_details[0].outcome == "no_grounded_items"


def test_model_error_still_ships_snippet_card():
    adapter = DocumentListCardAdapter(Chat(fail=True))
    (card,) = run(adapter, [DOC])
    assert card.summary == DOC.snippet and adapter.last_details[0].outcome == "error"


def test_no_docs_is_no_relevant_document():  # B-6
    assert run(DocumentListCardAdapter(Chat()), []) == []


def test_doc_without_id_never_becomes_card():  # B-5
    blank = RetrievedDoc(doc_id="", title="t", snippet="s", score=1.0)
    assert run(DocumentListCardAdapter(Chat()), [blank]) == []


def test_asks_for_json_schema_and_reads_it():
    chat = Chat(content='{"documents": ["위임장 (서명 필수)", "대리인 신분증"]}')
    (card,) = run(DocumentListCardAdapter(chat), [DOC])
    assert chat.schema["required"] == ["documents"]
    assert card.summary == "필요 서류: 위임장 · 대리인 신분증"


def test_empty_json_array_is_none_answer():
    adapter = DocumentListCardAdapter(Chat(content='{"documents": []}'))
    (card,) = run(adapter, [DOC])
    assert card.summary == DOC.snippet and adapter.last_details[0].outcome == "none"
