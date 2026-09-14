# Requirement: A-6
"""HTTP 표면 스키마 — 테스트 음성 업로드·보관. 숫자는 `StrField` 로 문자열이 되어 나간다."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ._types import StrField


class UploadTicketRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=200, description="원본 파일명. 서버가 정규화한다")
    content_type: str = Field(min_length=1, max_length=100, description="음성 MIME 만 허용")
    content_length: int = Field(gt=0, description="바이트. S3 정책이 실제 크기로 한 번 더 검사한다")


class UploadTicketSchema(BaseModel):
    url: str = Field(description="여기로 multipart POST 한다")
    fields: dict[str, str] = Field(description="그대로 폼에 싣는다. `file` 은 **맨 뒤**여야 한다")
    key: str
    expires_in: StrField = Field(description="초")


class StoredUploadSchema(BaseModel):
    key: str
    size: StrField
    last_modified: datetime


class StoredUploadListSchema(BaseModel):
    items: list[StoredUploadSchema]
    total: StrField


class DownloadTicketRequest(BaseModel):
    key: str = Field(min_length=1, max_length=400, description="목록이 돌려준 키 그대로")


class DownloadTicketSchema(BaseModel):
    url: str
    key: str
    expires_in: StrField
