# Requirement: J-2, J-4
"""HTTP 표면 스키마 — 상담원의 「내 요청」. 관리자 목록(`BlacklistRequestItemSchema`)보다 좁다.

**싣지 않는 것**: 고객 식별자(`customer_ref`, HMAC) · 결정한 관리자(`decided_by`) · 근거 건수. 상담원이 자기 요청의 결과를 아는 데
필요 없는 것을 내보내지 않는다. 사유·반려 사유는 저장 전에 마스킹된 값이다.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from hub.app.dtos.blacklist_dto import BlacklistRequest


class MyBlacklistRequestItemSchema(BaseModel):
    request_id: str
    call_id: str
    reason: str = Field(description="내가 적은 사유(마스킹본)")
    status: str = Field(description="pending · approved · rejected")
    requested_at: str
    decided_at: str | None = None
    decision_note: str | None = Field(default=None, description="반려 사유(마스킹본). 승인·대기면 null")

    @staticmethod
    def from_dto(r: BlacklistRequest) -> "MyBlacklistRequestItemSchema":
        return MyBlacklistRequestItemSchema(
            request_id=r.request_id, call_id=r.call_id, reason=r.reason, status=r.status,
            requested_at=r.requested_at.isoformat() if r.requested_at else "",
            decided_at=r.decided_at.isoformat() if r.decided_at else None,
            decision_note=r.decision_note,
        )


class MyBlacklistRequestListResponse(BaseModel):
    requests: list[MyBlacklistRequestItemSchema]
