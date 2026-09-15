# Requirement: A-6, SEC-1, SEC-2
"""테스트 음성 업로드·보관 — 발급 티켓과 보관 목록.

브라우저는 **AWS 자격증명을 들지 않는다.** 서버가 S3 presigned POST 를 발급하고, 브라우저는
그 URL 로만 올린다. 근거·되돌리는 법: `_project/decisions/110`.

**presigned POST 를 쓴다(PUT 이 아니다).** POST 정책에만 `content-length-range` 조건을 걸 수
있어 **크기 상한을 서버가 강제**한다. presigned PUT 은 크기를 못 걸어 링크 하나로 수십 GB 가 올라간다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class UploadTicketCommand:
    """브라우저가 「이 파일을 올리고 싶다」고 말한 것. **아직 아무것도 믿지 않는다.**"""

    filename: str
    content_type: str
    content_length: int


@dataclass(frozen=True)
class UploadTicket:
    """S3 에 직접 올릴 수 있는 일회용 티켓.

    `fields` 는 S3 가 요구하는 폼 필드(정책·서명 포함)다. 브라우저는 이걸 그대로 multipart 로
    싣고 마지막에 `file` 을 붙인다. 순서가 중요하다 — `file` 이 맨 뒤여야 한다(S3 규칙).
    """

    url: str
    fields: dict[str, str] = field(default_factory=dict)
    key: str = ""
    expires_in: int = 0


@dataclass(frozen=True)
class StoredUpload:
    """보관된 파일 하나. 내용이 아니라 **목록에 필요한 것만** 담는다."""

    key: str
    size: int
    last_modified: datetime


@dataclass(frozen=True)
class DownloadTicket:
    """다시 듣기용 일회용 링크. 객체를 공개로 만들지 않는다(`110` 9번)."""

    url: str
    key: str
    expires_in: int
