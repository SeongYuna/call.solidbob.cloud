# Requirement: B-2, B-3
from __future__ import annotations

from dataclasses import dataclass

from .retrieved_doc_dto import RetrievedDoc

DEFAULT_TOP_K = 5
MAX_TOP_K = 20


@dataclass(frozen=True)
class SearchQuery:
    """상담원이 직접 던지는 검색 1건. 자동 추천(B-1 트리거)이 빗나갔을 때의 폴백 경로다.

    `utterance` 는 이미 마스킹을 거친 화면 텍스트이거나 상담원이 손으로 친 질의다 —
    콜 미디에이터가 밀어넣는 원문(TranscriptIngestCommand)과 달리 이 DTO 에는 원문이 오지 않는다.
    """

    utterance: str
    top_k: int = DEFAULT_TOP_K


@dataclass(frozen=True)
class SearchResult:
    """검색 결과. 카드(B-4)로 다듬기 전 단계라 조항 목록 그대로다."""

    query: str
    docs: tuple[RetrievedDoc, ...]
