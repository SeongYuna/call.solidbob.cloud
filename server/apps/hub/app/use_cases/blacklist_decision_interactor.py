# Requirement: J-4, SEC-1
"""결정 인터랙터 — 만료 일수를 시각으로 바꾸고 메모를 마스킹해 포트에 넘긴다.

상태 전이(누가 무엇을 할 수 있는가)는 **포트 구현이 도메인 규칙으로** 확인한다. 여기서 if 로 다시 판단하지 않는다.
만료 기본값을 두지 않는다 — 「90일이 옳다」는 근거가 없다(절대 원칙 2, `decisions/304`).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from hub.app.dtos.blacklist_decision_dto import MAX_EXPIRES_IN_DAYS, BlacklistDecisionCommand
from hub.app.dtos.blacklist_dto import BlacklistRequest
from hub.app.ports.input.blacklist_decision_use_case import BlacklistDecisionUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.ports.output.masking_port import MaskingPort

NOTE_MAX_CHARS = 500  # `blacklist_entry.note` VARCHAR(500)


class BlacklistDecisionInteractor(BlacklistDecisionUseCase):
    def __init__(
        self, blacklist: BlacklistPort, masking: MaskingPort, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    ) -> None:
        self._blacklist = blacklist
        self._masking = masking
        self._now = now

    async def decide(self, command: BlacklistDecisionCommand) -> BlacklistRequest:
        expires_at = None
        if command.approve:
            days = command.expires_in_days
            if days is None or not 1 <= days <= MAX_EXPIRES_IN_DAYS:
                raise ValueError(f"승인에는 만료 일수(1~{MAX_EXPIRES_IN_DAYS})가 필요합니다")
            expires_at = self._now() + timedelta(days=days)
        note = None
        if command.approve and command.note and command.note.strip():
            note = self._masking.mask(command.note.strip())[0][:NOTE_MAX_CHARS]
        return await self._blacklist.decide(
            command.request_id, approve=command.approve, decided_by=command.decided_by, expires_at=expires_at, note=note
        )
