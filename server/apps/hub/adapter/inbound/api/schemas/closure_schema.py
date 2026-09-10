# Requirement: 7.3절 종결 판정, F-2
"""HTTP 표면 스키마. 필드명은 7.3절 종결 계약 JSON 과 같다."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ._types import StrField

from .recommendation_schema import SourceSchema


class ClosureCheckRequest(BaseModel):
    call_id: str
    closure_type: str = Field(min_length=1, description="도메인별 처리유형 — 상품해지·보상·반품·교환")
    evidence: dict[str, bool] = Field(min_length=1, description="closure_type 별 부분집합만")
    reason: str | None = None


class ClosureVerdictResponse(BaseModel):
    call_id: str
    closure_type: str
    evidence: dict[str, StrField]
    verdict: Literal["approved", "blocked"]
    missing: list[str] = Field(description="evidence 중 false 인 키만")
    reason: str | None = None
    source: SourceSchema | None = Field(default=None, description="판정 근거 규정 (*-POLICY-*)")
