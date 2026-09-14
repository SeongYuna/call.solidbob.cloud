# Requirement: A-6
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.upload_dto import DownloadTicket, StoredUpload, UploadTicket


class UploadStoragePort(ABC):
    """객체 저장소. I/O 포트라 async (구현체도 async — LSP).

    **여기는 「어디에 어떻게」만 안다.** 무엇을 허용할지(크기·형식·키 모양)는 인터랙터가 정해
    인자로 넘긴다 — 저장소를 S3 에서 다른 것으로 바꿔도 규칙이 따라가지 않게 하려는 것이다.
    """

    @abstractmethod
    async def issue_upload_ticket(
        self, key: str, content_type: str, max_bytes: int, expires_in: int
    ) -> UploadTicket: ...

    @abstractmethod
    async def list_objects(self, prefix: str, limit: int) -> list[StoredUpload]: ...

    @abstractmethod
    async def issue_download_ticket(self, key: str, expires_in: int) -> DownloadTicket: ...
