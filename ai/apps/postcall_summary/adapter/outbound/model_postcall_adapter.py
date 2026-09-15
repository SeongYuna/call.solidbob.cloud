# Requirement: D-1, D-2, D-3, SEC-1
"""`PostcallPort` 구현 — **규칙 발췌 초안(`server/apps/postcall`) 위에** 모델 요약(D-1)과 검색 기반 유형 제안(D-2)을 얹는다 (`w7-postcall-spoke`).

    자막(마스킹본) ─▶ fallback.summarize()          규칙 초안: 발췌 요약 · 유형 None · 약속 발화 후속조치(D-3)
                  ├▶ chat(요약) → summary_problems   통과하면 summary_text 교체, 걸리면 발췌 그대로
                  └▶ retrieval(고객 발화) → 장 투표   inquiry_type 제안

**D-3 후속조치는 규칙 초안 것을 그대로 쓴다** — 모델에게 «할 일» 을 뽑게 하면 약속하지 않은 일을 지어낼 수 있고, 그건 상담원이 해야 할 일로 저장된다.
**`confirmed` 는 항상 False** — 계약이 모델 출력을 확정으로 받지 않는다(서버도 덮어쓴다).
**요약 문자열에 손대지 않는다**(끝에 표시만 붙인다) — 모델 출력과 화면이 달라지면 환각 추적이 끊긴다(`w7-postcall-contract`).

`fallback`·`retrieval`·`chat` 은 전부 주입이다 — `server/apps/postcall`·`ai/apps/retrieval`·`ai/apps/generation` 을 import 하지 않는다(계약 2).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from typing import Protocol

from hub.app.dtos.call_summary_dto import CallSummaryDraft
from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.output.postcall_port import PostcallPort
from hub.app.ports.output.retrieval_port import RetrievalPort

from ...domain.services.rules import build_messages, suggest_inquiry_type, summary_problems

log = logging.getLogger(__name__)

MODEL_SUMMARY_MARK = " (모델 요약 초안)"
MAX_QUERY_CHARS = 400  # 검색에 넣을 고객 발화 합의 상한 — 통화 전체를 넣으면 임베딩 512토큰에서 잘린다


class ChatClient(Protocol):
    model: str

    def chat(self, messages: list[dict[str, str]], *, schema: dict | None = None): ...


@dataclass
class PostcallDetail:
    summary_source: str = "rule"  # "model" | "rule"
    problems: tuple[str, ...] = ()
    raw_summary: str = ""
    elapsed_ms: float = 0.0
    retrieved: tuple[str, ...] = ()


class ModelPostcallAdapter(PostcallPort):
    def __init__(self, fallback: PostcallPort, *, chat: ChatClient | None, retrieval: RetrievalPort | None) -> None:
        self._fallback = fallback
        self._chat = chat
        self._retrieval = retrieval
        self.last_detail = PostcallDetail()

    async def summarize(self, call_id: str, segments: list[TranscriptEvent]) -> CallSummaryDraft:
        draft = await self._fallback.summarize(call_id, segments)
        finals = sorted((s for s in segments if s.is_final and s.text.strip()), key=lambda s: s.segment_id)
        detail = PostcallDetail()

        inquiry_type = draft.inquiry_type
        if self._retrieval is not None:
            query = " ".join(s.text for s in finals if s.speaker == "customer")[:MAX_QUERY_CHARS]
            if query.strip():
                try:
                    docs = await self._retrieval.retrieve(query, top_k=5)
                    detail.retrieved = tuple(d.doc_id for d in docs)
                    inquiry_type = suggest_inquiry_type(detail.retrieved) or inquiry_type
                except Exception as e:  # noqa: BLE001 — 유형 제안이 없어도 초안은 나간다
                    log.warning("유형 제안 검색 실패: %s", type(e).__name__)

        summary_text = draft.summary_text
        if self._chat is not None and finals:
            lines = [(s.speaker, s.text) for s in finals]
            try:
                res = await asyncio.to_thread(self._chat.chat, build_messages(lines))
                detail.raw_summary, detail.elapsed_ms = res.content, res.elapsed_ms
                detail.problems = tuple(summary_problems(res.content, "\n".join(t for _, t in lines)))
                if not detail.problems:
                    summary_text = res.content.strip() + MODEL_SUMMARY_MARK
                    detail.summary_source = "model"
            except Exception as e:  # noqa: BLE001 — 모델이 죽어도 규칙 초안은 나간다
                detail.problems = (f"모델 호출 실패 {type(e).__name__}",)

        self.last_detail = detail
        return replace(draft, summary_text=summary_text, inquiry_type=inquiry_type, confirmed=False)
