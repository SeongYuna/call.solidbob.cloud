# Requirement: J-4
"""HTTP 표면 스키마 — 블랙리스트 보존 기간 정리 결과. 값은 전부 문자열이다(`_types.StrField`)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField


class RetentionPurgeResponse(BaseModel):
    retention_days: StrField = Field(description="보존 기간(일) — 끝난 뒤 이만큼 지나면 비운다")
    cutoff: str = Field(description="이 시각 이전에 끝난 것만 비웠다")
    expiry_change_reasons_purged: StrField = Field(description="비운 만료 변경 사유 건수")
    rejected_requests_purged: StrField = Field(description="사유·자막을 비운 반려 요청 건수")
