# Requirement: D-1, D-2, D-3, SEC-1
from __future__ import annotations

from dataclasses import dataclass, field

from .transcript_dto import Speaker


@dataclass(frozen=True)
class PostcallSegment:
    """화면이 들고 있던 자막 1건 — **원문일 수 있다**(`decisions/326`).

    2026-10-06 부터 상담원 화면은 원문 자막을 보여 준다. `/close` 는 그 화면이 들고 있던 자막을 그대로 받으므로
    여기 담긴 글은 마스킹 전일 수 있다. 그래서 `TranscriptEvent`(마스킹 완료본만)가 아니라 이 모양으로 받고,
    postcall 인터랙터가 MaskingPort 를 거친 `TranscriptEvent` 로 바꾼 뒤에야 요약·저장으로 넘긴다."""

    segment_id: int
    speaker: Speaker
    raw_text: str
    is_final: bool
    utterance_end_ms: int | None = None


@dataclass(frozen=True)
class PostcallCommand:
    """통화 종료 요청. 전사는 마스킹 전일 수 있다 — 인터랙터가 요약 전에 가린다 (SEC-1)."""

    call_id: str
    segments: tuple[PostcallSegment, ...] = field(default_factory=tuple)
