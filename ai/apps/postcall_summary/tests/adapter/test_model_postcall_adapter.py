# Requirement: D-1, D-2, D-3, SEC-1
"""규칙 초안 위에 모델 요약·유형 제안을 얹는 배선. 가짜 포트로 고정한다."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from hub.app.dtos.call_summary_dto import CallSummaryDraft, FollowUpAction
from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.output.postcall_port import PostcallPort
from hub.app.ports.output.retrieval_port import RetrievalPort

from postcall_summary.adapter.outbound.model_postcall_adapter import MODEL_SUMMARY_MARK, ModelPostcallAdapter


class Rule(PostcallPort):
    async def summarize(self, call_id, segments):
        return CallSummaryDraft(call_id=call_id, summary_text="고객 문의: … (규칙 발췌 초안)",
                                follow_up_actions=(FollowUpAction("문자로 보내드리겠습니다"),), confirmed=True)


class Search(RetrievalPort):
    def __init__(self):
        self.queries = []

    async def retrieve(self, utterance, top_k=5):
        self.queries.append(utterance)
        return [RetrievedDoc(doc_id="DASAN-TERM-3.2", title="t", snippet="s", score=1.0)]


@dataclass
class Res:
    content: str
    elapsed_ms: float = 5.0


class Chat:
    model = "fake"

    def __init__(self, content="고객이 수도요금 32150원 납부를 문의했고 상담원이 가상계좌를 안내했다.", fail=False):
        self.content, self.fail = content, fail

    def chat(self, messages, schema=None):
        if self.fail:
            raise TimeoutError()
        return Res(self.content)


SEGS = [
    TranscriptEvent(call_id="c1", segment_id=2, speaker="agent", text="가상계좌로 입금하시면 됩니다", is_final=True),
    TranscriptEvent(call_id="c1", segment_id=1, speaker="customer", text="수도요금 32150원 어떻게 내요", is_final=True),
    TranscriptEvent(call_id="c1", segment_id=3, speaker="customer", text="수도요", is_final=False),  # interim 은 버린다
]


def run(adapter):
    return asyncio.run(adapter.summarize("c1", SEGS))


def test_model_summary_and_type_layered_on_rule_draft():
    search = Search()
    adapter = ModelPostcallAdapter(Rule(), chat=Chat(), retrieval=search)
    d = run(adapter)
    assert d.summary_text.endswith(MODEL_SUMMARY_MARK) and adapter.last_detail.summary_source == "model"
    assert d.inquiry_type == "생활하수도 관련 문의"
    assert d.follow_up_actions == (FollowUpAction("문자로 보내드리겠습니다"),)  # D-3 은 규칙 것 그대로
    assert d.confirmed is False  # 규칙 초안이 True 로 줘도 덮는다
    assert search.queries == ["수도요금 32150원 어떻게 내요"]  # 고객 확정 발화만 검색한다


def test_invented_number_falls_back_to_rule_summary():
    adapter = ModelPostcallAdapter(Rule(), chat=Chat(content="수도요금 50000원을 안내했다."), retrieval=None)
    d = run(adapter)
    assert d.summary_text == "고객 문의: … (규칙 발췌 초안)" and adapter.last_detail.summary_source == "rule"
    assert adapter.last_detail.problems == ("자막에 없는 숫자 50000",)


def test_model_failure_keeps_rule_draft():
    d = run(ModelPostcallAdapter(Rule(), chat=Chat(fail=True), retrieval=None))
    assert d.summary_text.endswith("(규칙 발췌 초안)") and d.inquiry_type is None


def test_without_model_or_search_is_rule_draft():
    d = run(ModelPostcallAdapter(Rule(), chat=None, retrieval=None))
    assert d.summary_text.endswith("(규칙 발췌 초안)") and d.confirmed is False
