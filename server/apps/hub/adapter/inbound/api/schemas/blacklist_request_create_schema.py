# Requirement: J-1, J-2
"""HTTP 표면 스키마 — 블랙리스트 요청. 필드명은 db `blacklist_request` · 프론트 `BlacklistRequestItem` 과 같고,
값은 전부 문자열이다(`_types.StrField`). 목록·결정 응답도 같은 항목 스키마를 쓴다."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField

from hub.app.dtos.blacklist_dto import BlacklistRequest


class BlacklistRequestCreateRequest(BaseModel):
    """요청자는 본문에 없다 — 상담원 토큰에서 온다(`decisions/307`). 본문에 `requested_by` 를 실어도 무시된다."""

    call_id: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=2000, description="상담원이 적은 사유. 저장 전에 마스킹하고 500자로 자른다")


class BlacklistEvidenceSchema(BaseModel):
    call_duration_s: StrField
    insult_count: StrField
    threat_count: StrField
    sexual_count: StrField
    temperature_outliers: StrField | None = Field(default=None, description="null 은 「미측정」 — 0(이상 없음)과 다르다(decisions/316)")


class BlacklistRequestItemSchema(BaseModel):
    request_id: str
    call_id: str
    customer_ref: str = Field(description="발신 번호의 HMAC — 평문이 아니다")
    display_hint: str | None = Field(default=None, description="⚠ 채우지 않는다 — 늘 null(decisions/316, 전화번호 뒷자리도 P4)")
    requested_by: str
    reason: str = Field(description="마스킹된 사유")
    context_excerpt: str = Field(description="마스킹된 자막에서 서버가 자른 것")
    evidence: BlacklistEvidenceSchema = Field(description="건수·시간뿐 — 점수가 아니다(부록 A-1). distress 건수는 저장되지 않아 목록에 없다")
    status: str
    requested_at: str
    decided_by: str | None = None
    decided_at: str | None = None
    evidence_snapshot_at: str
    decision_note: str | None = Field(default=None, description="반려 사유(마스킹본). 승인이면 null — 승인 메모는 등록 쪽 note")

    @staticmethod
    def from_dto(r: BlacklistRequest) -> "BlacklistRequestItemSchema":
        e = r.evidence
        return BlacklistRequestItemSchema(
            request_id=r.request_id, call_id=r.call_id, customer_ref=r.customer_ref, requested_by=r.requested_by,
            reason=r.reason, context_excerpt=r.context_excerpt,
            evidence=BlacklistEvidenceSchema(
                call_duration_s=e.call_duration_s, insult_count=e.insult_count, threat_count=e.threat_count,
                sexual_count=e.sexual_count, temperature_outliers=e.temperature_outliers,
            ),
            status=r.status,
            requested_at=r.requested_at.isoformat() if r.requested_at else "",
            decided_by=r.decided_by,
            decided_at=r.decided_at.isoformat() if r.decided_at else None,
            evidence_snapshot_at=r.evidence_snapshot_at.isoformat() if r.evidence_snapshot_at else "",
            decision_note=r.decision_note,
        )


class BlacklistRequestCreatedResponse(BaseModel):
    request: BlacklistRequestItemSchema
    has_distress: StrField = Field(
        description="위기 신호가 섞였다 — 화면은 차단이 아니라 전문 기관 연결 안내를 띄운다(MANUAL-5.4). 저장되지 않는 값"
    )
