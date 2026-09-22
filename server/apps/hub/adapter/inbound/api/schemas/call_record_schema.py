# Requirement: B-5, D-1, D-2, D-3, F-2
"""HTTP 표면 스키마 — 통화 1건의 저장 기록. 값은 전부 문자열이다(`_types.StrField`, 7.3절 규칙)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField


class SavedCardSchema(BaseModel):
    card_id: StrField = Field(description="카드 피드백(POST /hub/cards/{card_id}/feedback)에 쓴다")
    rank: StrField
    title: str
    summary: str
    source_doc_id: str | None = Field(default=None, description="document 에 없는 조항이면 null 로 저장됐다")
    similarity_score: StrField | None = None


class SavedRecommendationSchema(BaseModel):
    recommendation_id: StrField
    trigger_at_ms: StrField
    internal_latency_ms: StrField | None = None
    created_at: str
    cards: list[SavedCardSchema] = Field(description="비었으면 「관련 문서 없음」(B-6)")


class SavedClosureItemSchema(BaseModel):
    rank: StrField
    document_name: str
    informed: StrField


class SavedClosureSchema(BaseModel):
    closure_id: StrField
    procedure: str
    verdict: str = Field(description="complete | incomplete — 차단이 아니라 경고다")
    detected: StrField = Field(description="true 면 상담원 발화 키워드로 자동 판정 — 부정 문맥을 모른다")
    reason: str | None = None
    source_doc_id: str | None = None
    decided_at: str
    items: list[SavedClosureItemSchema]


class SavedFollowUpSchema(BaseModel):
    action_text: str
    status: str = Field(description="draft = 규칙·모델 초안")


class CallRecordResponse(BaseModel):
    call_id: str
    status: str
    started_at: str
    ended_at: str | None = None
    summary_text: str | None = Field(default=None, description="D-1 초안(규칙 발췌, decisions/306). 통화 후 처리 전이면 null")
    inquiry_type: str | None = Field(default=None, description="D-2 제안 — 지식베이스 장 이름 또는 「미분류」(decisions/323). 통화 후 처리 전이면 null")
    customer_id: str | None = Field(default=None, description="전화번호 HMAC-SHA256 hex 64자(decisions/304) — 원본 번호가 아니다. 발신 번호가 없던 통화는 null")
    summary_confirmed: StrField = Field(description="상담원이 확정했는가. false 면 초안이거나 아직 없다")
    follow_up_actions: list[SavedFollowUpSchema]
    recommendations: list[SavedRecommendationSchema] = Field(description="발동한 추천만, 만든 순서. 추천 저장 이전(0.1.9 전) 통화는 비어 있다")
    closures: list[SavedClosureSchema] = Field(description="필요서류 체크리스트 판정, 판정 순(append-only)")
