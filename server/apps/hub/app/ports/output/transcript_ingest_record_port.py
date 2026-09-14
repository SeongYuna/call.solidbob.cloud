# Requirement: 7.3절 전사 이벤트, SEC-1
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.transcript_dto import TranscriptEvent


class CallNotStartedError(Exception):
    """`call` 행이 없는 통화의 전사를 저장하려 했다 — `POST /hub/calls` 가 먼저 와야 한다(`decisions/301`).

    코드 결함이 아니라 **호출 순서** 문제라 500 으로 두지 않는다. 500 은 "서버가 틀렸다"로 읽혀
    고칠 사람을 잘못 찾게 만든다(2026-09-11 운영에서 실제로 그렇게 읽혔다).
    """

    def __init__(self, call_id: str) -> None:
        super().__init__(call_id)
        self.call_id = call_id


class TranscriptIngestRecordPort(ABC):
    """전사 수신 활동 기록. 마스킹 **후** 이벤트만 받는다 — 원문을 받는 시그니처는 만들지 않는다 (SEC-1).
    지금은 로그 어댑터, 3주차에 PostgreSQL transcript_segment 어댑터로 교체. I/O 포트라 async (구현체도 async — LSP)."""

    @abstractmethod
    async def record(self, event: TranscriptEvent) -> None:
        """통화(`call`)가 없으면 `CallNotStartedError` 를 올린다. 저장소가 외래키를 모르면(로그 어댑터) 올리지 않는다."""
