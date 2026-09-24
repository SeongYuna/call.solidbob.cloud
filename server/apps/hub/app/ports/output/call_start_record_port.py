# Requirement: 7.3절 전사 이벤트
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.call_start_dto import CallStarted


class CallStartRecordPort(ABC):
    """통화 시작 기록. `call` 행을 만든다. I/O 포트라 async (구현체도 async — LSP).

    이미 같은 `call_id` 가 있으면 건드리지 않고 False 를 돌려준다 — 콜 미디에이터가 재시도해도
    통화가 둘이 되거나 시작 시각이 덮이지 않는다."""

    @abstractmethod
    async def record(self, call: CallStarted) -> bool: ...

    async def last_segment_id(self, call_id: str) -> int:
        """이 통화에 이미 저장된 가장 큰 `segment_id`. 없으면 0.

        콜 미디에이터가 같은 통화를 **다시 열 때**(파드 재시작·연결 끊김 뒤 재연결) 발화 번호를 여기서 이어 센다 —
        1부터 다시 세면 저장된 전사를 같은 번호로 덮어쓴다(2026-09-22 운영 QA `test-qa-05`, `w6-segment-id-reuse`).
        저장하지 않는 구현(로그 어댑터)은 기본값 0 을 쓴다 — 덮어쓸 것이 없다."""
        return 0
