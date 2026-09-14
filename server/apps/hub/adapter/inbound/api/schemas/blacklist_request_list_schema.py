# Requirement: J-4
"""HTTP 표면 스키마 — 요청 목록. 항목은 요청 생성과 같은 모양이다."""

from __future__ import annotations

from pydantic import BaseModel

from .blacklist_request_create_schema import BlacklistRequestItemSchema


class BlacklistRequestListResponse(BaseModel):
    requests: list[BlacklistRequestItemSchema]
