# Requirement: 7.3절 종결 판정, F-2
"""HTTP 표면 스키마 — 필요서류 체크리스트. 필드명은 `plan.md` 7.3절 rev.5 계약과 같고 값은 전부 문자열이다.
자동 판정(`required_docs_detection_schema`)도 같은 응답을 쓴다."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ._types import StrField

from .recommendation_schema import SourceSchema

from hub.app.dtos.closure_verdict_dto import ClosureVerdict


class ClosureCheckRequest(BaseModel):
    call_id: str
    procedure: str = Field(min_length=1, max_length=30, description="필요서류 조항 ID (예: DASAN-TERM-4.4)")
    evidence: dict[str, bool] = Field(min_length=1, description="서류 이름 → 안내했는가")
    reason: str | None = None


class ClosureVerdictResponse(BaseModel):
    call_id: str
    procedure: str
    procedure_title: str | None = None
    evidence: dict[str, StrField] = Field(description="규칙표의 필수 서류만 — 순서가 규칙표 순서다")
    verdict: Literal["complete", "incomplete"] = Field(description="차단이 아니라 경고다(rev.5)")
    missing: list[str] = Field(description="안내하지 않은 필수 서류 — 빠짐없이")
    conditional: list[str] = Field(default_factory=list, description="조건부 추가 서류 — 판정에 넣지 않았다")
    reason: str | None = None
    source: SourceSchema | None = Field(default=None, description="판정 근거 조항 (DASAN-TERM-x.y)")
    detected: StrField = Field(description="true 면 상담원 발화 키워드로 자동 판정했다 — 부정 문맥을 모른다")

    @staticmethod
    def from_dto(v: ClosureVerdict) -> "ClosureVerdictResponse":
        return ClosureVerdictResponse(
            call_id=v.call_id, procedure=v.procedure, procedure_title=v.procedure_title, evidence=v.evidence,
            verdict=v.verdict, missing=list(v.missing), conditional=list(v.conditional), reason=v.reason,
            source=SourceSchema(doc_id=v.source.doc_id, title=v.source.title) if v.source else None,
            detected=v.detected,
        )
