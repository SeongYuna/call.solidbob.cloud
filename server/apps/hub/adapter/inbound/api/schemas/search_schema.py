# Requirement: B-2, B-3, B-6
"""HTTP 표면 스키마. 필드명은 7.3절 카드 계약의 `source` 와 같은 이름을 쓴다
(대시보드가 자동 추천 카드와 수동 검색 결과를 같은 모양으로 다룬다)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField

from hub.app.dtos.search_dto import DEFAULT_TOP_K, MAX_TOP_K


class SearchRequest(BaseModel):
    utterance: str = Field(min_length=1, description="상담원이 찾는 말. 마스킹된 화면 텍스트이거나 직접 입력")
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAX_TOP_K)


class RetrievedDocSchema(BaseModel):
    doc_id: str = Field(description="knowledge-base 조항 ID. 항상 존재한다 — 출처 없는 결과는 내지 않는다 (B-6)")
    title: str
    snippet: str
    score: StrField


class SearchResponse(BaseModel):
    query: str
    docs: list[RetrievedDocSchema]
