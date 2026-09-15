# Requirement: D-1, D-2, D-3, SEC-1
"""요약 확정 인터랙터 — 입력을 확인하고 **사람이 쓴 문구를 마스킹**해 포트에 넘긴다.

초안은 마스킹된 자막에서 나왔지만, 상담원이 고친 문구에는 이름·번호가 새로 섞일 수 있다(블랙리스트 사유와 같은 이유, `decisions/205` ⑤).
이미 확정됐는지는 여기서 판단하지 않는다 — 저장소가 `SummaryAlreadyConfirmedError` 로 막는다.
"""

from __future__ import annotations

from hub.app.dtos.summary_confirmation_dto import (
    ACTION_MAX_CHARS,
    INQUIRY_TYPE_MAX_CHARS,
    MAX_FOLLOW_UPS,
    SummaryConfirmationCommand,
    SummaryConfirmed,
)
from hub.app.ports.input.summary_confirmation_use_case import SummaryConfirmationUseCase
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.summary_confirmation_port import SummaryConfirmationPort


class SummaryConfirmationInteractor(SummaryConfirmationUseCase):
    def __init__(self, confirmation: SummaryConfirmationPort, masking: MaskingPort) -> None:
        self._confirmation = confirmation
        self._masking = masking

    def _mask(self, text: str) -> str:
        return self._masking.mask(text.strip())[0]

    async def confirm(self, command: SummaryConfirmationCommand) -> SummaryConfirmed:
        if not command.summary_text.strip():
            raise ValueError("요약이 비어 있습니다 — 확정할 내용이 없습니다")
        actions = [a for a in command.follow_up_actions if a.strip()]
        if len(actions) > MAX_FOLLOW_UPS:
            raise ValueError(f"후속조치는 {MAX_FOLLOW_UPS}건까지입니다: {len(actions)}")
        inquiry = command.inquiry_type.strip() if command.inquiry_type and command.inquiry_type.strip() else None
        if inquiry is not None and len(inquiry) > INQUIRY_TYPE_MAX_CHARS:
            raise ValueError(f"유형은 {INQUIRY_TYPE_MAX_CHARS}자까지입니다")

        summary = self._mask(command.summary_text)
        masked_inquiry = self._mask(inquiry) if inquiry is not None else None
        masked_actions = tuple(self._mask(a)[:ACTION_MAX_CHARS] for a in actions)
        confirmed_at = await self._confirmation.confirm(
            command.call_id, summary_text=summary, inquiry_type=masked_inquiry, follow_up_actions=masked_actions
        )
        return SummaryConfirmed(call_id=command.call_id, summary_text=summary, inquiry_type=masked_inquiry,
                                follow_up_actions=masked_actions, confirmed_at=confirmed_at)
