# Requirement: 7.3절 전사 이벤트, C-5, SEC-1
from __future__ import annotations

from dataclasses import dataclass

from .transcript_dto import Speaker


@dataclass(frozen=True)
class TranscriptIngestCommand:
    """콜 미디에이터가 밀어넣는 전사 1건 — **마스킹 전 원문**을 담는 유일한 DTO.

    이 객체는 transcript_ingest 인터랙터 안에서만 살고, 인터랙터가 MaskingPort 를 거친 TranscriptEvent 로
    바꾼 뒤에는 어디에도 남기지 않는다(로그·기록 포트에도 넘기지 않는다 — SEC-1)."""

    call_id: str
    segment_id: int
    speaker: Speaker
    raw_text: str
    is_final: bool
    utterance_end_ms: int | None = None
