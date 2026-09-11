# Requirement: 7.3절 추천 카드, B-1, B-5, B-6
"""HTTP 표면 스키마. 응답 필드명은 7.3절 카드 계약 JSON 과 글자 단위로 같다."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ._types import StrField


class RecommendRequest(BaseModel):
    """마스킹을 이미 거친 전사 이벤트. 원문 필드는 없다 (SEC-1)."""

    call_id: str
    segment_id: int = Field(description="정수 또는 숫자 문자열('12') — 응답은 문자열로 나간다 (7.3절)")
    speaker: Literal["customer", "agent"]
    text: str = Field(min_length=1, description="마스킹 완료본")
    is_final: bool
    utterance_end_ms: int | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SourceSchema(BaseModel):
    doc_id: str
    title: str


class CardSchema(BaseModel):
    title: str
    summary: str
    source: SourceSchema  # 필수 — 출처 없는 카드는 만들지 않는다 (B-5)
    similarity_score: StrField  # 7.3절 계약 필드명. DB recommendation_card.similarity_score 와 같다 (decisions/003)


class RecommendResponse(BaseModel):
    fired: StrField = Field(description="트리거 발동 여부. false 면 검색조차 하지 않았다")
    domain: str | None = Field(default=None, description="B-0 판정. 분류기가 없으면 null (전 도메인 검색)")
    call_id: str | None = None
    trigger_at_ms: StrField | None = None
    cards: list[CardSchema] | None = Field(
        default=None, description="fired=false 면 null. 빈 배열은 '관련 문서 없음'(B-6)"
    )
    internal_latency_ms: StrField | None = Field(default=None, description="트리거 → 카드 완성 (4.1절 p95 대상)")
