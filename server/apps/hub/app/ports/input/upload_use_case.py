# Requirement: A-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.upload_dto import (
    DownloadTicket,
    StoredUpload,
    UploadTicket,
    UploadTicketCommand,
)


class UploadUseCase(ABC):
    """테스트 음성 업로드·보관. 판정(허용 여부·키 생성)은 인터랙터가 규칙으로 한다."""

    @abstractmethod
    async def issue(self, command: UploadTicketCommand) -> UploadTicket:
        """업로드 티켓을 발급한다. 규칙에 어긋나면 `UploadRejected` 를 올린다."""

    @abstractmethod
    async def list_recent(self, limit: int) -> list[StoredUpload]:
        """최근 보관분. 새 것이 앞이다."""

    @abstractmethod
    async def issue_download(self, key: str) -> DownloadTicket:
        """다시 듣기 링크. 보관 프리픽스 밖의 키는 거절한다."""
