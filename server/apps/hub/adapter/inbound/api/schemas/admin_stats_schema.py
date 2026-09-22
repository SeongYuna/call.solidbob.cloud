# Requirement: J-3, J-5, C-6
"""HTTP 표면 스키마 — 관리자 현황판. 응답은 전부 문자열이다(§7.3 규칙)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField


class AdminStatsResponse(BaseModel):
    calls_total: StrField = Field(description="시작된 통화 전체")
    calls_closed: StrField = Field(description="닫힌 통화(POST /hub/calls/{id}/close). 09-20 이전 통화는 닫힌 적이 없다")
    call_guard_flags: StrField = Field(description="콜 가드(C-6) 신호 전체")
    pending_requests: StrField = Field(description="결정 대기 블랙리스트 요청")
    active_entries: StrField = Field(description="적용 중 블랙리스트 등록(해제 안 됨·만료 전)")
    routing_decisions: StrField = Field(description="J-5 배정 판정 전체 — 부르는 곳(콜 미디에이터, decisions/126)이 붙기 전엔 0")
    routing_blacklisted: StrField = Field(description="그중 블랙리스트 고객")
    routing_fell_back: StrField = Field(description="그중 베테랑이 없어 일반 배정으로 떨어진 건")
    counted_at: str = Field(description="DB 가 센 시각(ISO 8601)")
