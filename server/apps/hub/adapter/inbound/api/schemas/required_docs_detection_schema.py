# Requirement: F-2
"""HTTP 표면 스키마 — 필요서류 자동 판정 요청. 응답은 체크리스트와 같다(`closure_schema.ClosureVerdictResponse`)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RequiredDocsDetectionRequest(BaseModel):
    call_id: str
    procedure: str = Field(min_length=1, max_length=30, description="필요서류 조항 ID — 추천 카드 source.doc_id")
    agent_utterances: list[str] = Field(
        default_factory=list, max_length=500, description="그 통화 **상담원** 확정 발화의 **마스킹본**. 비어 있으면 전부 누락이다"
    )
