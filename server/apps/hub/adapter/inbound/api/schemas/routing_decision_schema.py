# Requirement: J-5
"""HTTP 표면 스키마 — 인입 배정 판정. 값은 전부 문자열이다(`_types.StrField`)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField

from hub.app.dtos.routing_decision_dto import MAX_CANDIDATES


class RoutingDecisionRequest(BaseModel):
    call_id: str = Field(min_length=1, max_length=40, description="POST /hub/calls 로 먼저 연 통화")
    candidates: list[str] = Field(default_factory=list, max_length=MAX_CANDIDATES,
                                  description="지금 받을 수 있는 상담사 agent_id — 부르는 쪽(교환기)이 준다. 서버는 대기 상태를 모른다")


class RoutingDecisionResponse(BaseModel):
    call_id: str
    assigned_agent_id: str | None = Field(default=None, description="연결할 상담사. null 이면 기존 배정 규칙을 따른다(블랙리스트 아님) 또는 후보가 없다")
    is_blacklisted: StrField
    fell_back: StrField = Field(description="true 면 베테랑이 없어 일반 배정으로 떨어졌다 — 셀 수 있게 남긴다")
    reason: str
    customer_identified: StrField = Field(description="false 면 발신 번호·HMAC 키가 없어 블랙리스트 여부를 볼 수 없었다")
    veteran_years: StrField = Field(description="이번 판정에 쓴 근속 기준")
    unknown_candidates: list[str] = Field(description="agent 에 없어 후보에서 뺀 ID")
