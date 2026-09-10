# Requirement: C-1, C-2, C-3, C-4
"""HTTP 표면 스키마. 필드명은 db `compliance_flag` 와 7.3절 카드 `source` 를 따른다."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .recommendation_schema import SourceSchema


class ComplianceCheckRequest(BaseModel):
    call_id: str
    segment_id: int
    agent_utterance: str = Field(min_length=1, description="상담원 발화만. 고객 발화는 검사하지 않는다")


class ComplianceFindingSchema(BaseModel):
    rule_code: str = Field(description="C-1 ~ C-3 (db: compliance_flag.rule_code)")
    phrase: str = Field(description="위반으로 잡힌 표현")
    alternative_source: SourceSchema | None = Field(default=None, description="C-4 권장 대체 표현 출처")


class ComplianceCheckResponse(BaseModel):
    call_id: str
    segment_id: str  # 7.3절 계약: 응답에서는 문자열 (DB 는 BIGINT, 경계에서만 변환 — 2026-09-10 조서희 요청)
    findings: list[ComplianceFindingSchema] = Field(
        description="빈 배열은 '잡힌 것이 없음'이지 '안전함'이 아니다 (부록 A-1)"
    )
