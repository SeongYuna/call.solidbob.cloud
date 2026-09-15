# Requirement: J-4, SEC-1
"""만료 변경 인터랙터 — 일수를 시각으로 바꾸고 사유를 마스킹해 포트에 넘긴다(`decisions/309`).

**연장인지 단축인지 가르지 않는다** — «지금부터 N일 뒤» 하나로 받는다. 이전 값과 새 값은 이력에 둘 다 남아 방향이 드러난다.
상한은 승인과 같은 365일이다 — 연장을 되풀이해 영구 표시를 만드는 것은 막지 못한다(이력으로 드러날 뿐, `decisions/309` 남는 것).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from hub.app.dtos.blacklist_decision_dto import MAX_EXPIRES_IN_DAYS
from hub.app.dtos.blacklist_expiry_change_dto import BlacklistExpiryChangeCommand, BlacklistExpiryChanged
from hub.app.ports.input.blacklist_expiry_change_use_case import BlacklistExpiryChangeUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.ports.output.masking_port import MaskingPort

REASON_MAX_CHARS = 500  # `blacklist_entry_expiry_change.reason` VARCHAR(500)


class BlacklistExpiryChangeInteractor(BlacklistExpiryChangeUseCase):
    def __init__(
        self, blacklist: BlacklistPort, masking: MaskingPort, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    ) -> None:
        self._blacklist = blacklist
        self._masking = masking
        self._now = now

    async def change(self, command: BlacklistExpiryChangeCommand) -> BlacklistExpiryChanged:
        if not 1 <= command.expires_in_days <= MAX_EXPIRES_IN_DAYS:
            raise ValueError(f"만료 일수는 1~{MAX_EXPIRES_IN_DAYS} 사이여야 합니다: {command.expires_in_days}")
        if not command.reason.strip():
            raise ValueError("변경 사유가 비어 있습니다")
        reason = self._masking.mask(command.reason.strip())[0][:REASON_MAX_CHARS]
        entry, change = await self._blacklist.change_expiry(
            command.entry_id,
            changed_by=command.changed_by,
            expires_at=self._now() + timedelta(days=command.expires_in_days),
            reason=reason,
        )
        return BlacklistExpiryChanged(entry=entry, change=change)
