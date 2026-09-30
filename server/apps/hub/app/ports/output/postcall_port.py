# Requirement: D-1, D-2, D-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_summary_dto import CallSummaryDraft
from hub.app.dtos.transcript_dto import TranscriptEvent


class PostcallPort(ABC):
    """D-1~D-3. 통화가 끝난 뒤 전사 전체로 요약·유형 제안·후속조치를 만든다. 모델 추론 → async.

    **마스킹된 전사만 받는다** (SEC-1). 통화 후 처리라고 원문을 다시 꺼내오지 않는다 —
    원문은 애초에 저장돼 있지 않다.

    돌려주는 것은 `CallSummaryDraft` 다. 확정본이 아니라 초안이라는 사실이 타입에 박혀 있다.
    """

    @abstractmethod
    async def summarize(self, call_id: str, segments: list[TranscriptEvent]) -> CallSummaryDraft: ...

    async def summarize_with_flags(
        self, call_id: str, segments: list[TranscriptEvent], flagged_segment_ids: frozenset[int]
    ) -> CallSummaryDraft:
        """컴플라이언스 위반이 잡힌 발화 번호를 같이 받는 판(2026-10-01) — 위반 문장을 「안내」로 싣지 않으려고.
        기본은 무시하고 `summarize` 로 — 모델 어댑터·테스트 스텁이 그대로 돈다. 규칙 어댑터가 덮어쓴다."""
        return await self.summarize(call_id, segments)
