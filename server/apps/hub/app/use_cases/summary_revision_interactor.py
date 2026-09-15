# Requirement: D-1, D-2, D-3, SEC-1
"""요약 재수정 인터랙터 — 확정과 같은 입력 검사 + 사유 필수, 사람이 쓴 문구를 전부 마스킹해 넘긴다.
확정됐는지는 여기서 판단하지 않는다 — 저장소가 `SummaryNotConfirmedError` 로 막는다."""

from __future__ import annotations

from hub.app.dtos.summary_confirmation_dto import ACTION_MAX_CHARS, INQUIRY_TYPE_MAX_CHARS, MAX_FOLLOW_UPS
from hub.app.dtos.summary_revision_dto import REASON_MAX_CHARS, SummaryRevisionCommand, SummaryRevised
from hub.app.ports.input.summary_revision_use_case import SummaryRevisionUseCase
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.summary_revision_port import SummaryRevisionPort


class SummaryRevisionInteractor(SummaryRevisionUseCase):
    def __init__(self, revisions: SummaryRevisionPort, masking: MaskingPort) -> None:
        self._revisions = revisions
        self._masking = masking

    def _mask(self, text: str) -> str:
        return self._masking.mask(text.strip())[0]

    async def revise(self, command: SummaryRevisionCommand) -> SummaryRevised:
        if not command.summary_text.strip():
            raise ValueError("요약이 비어 있습니다")
        if not command.reason.strip():
            raise ValueError("고치는 사유가 비어 있습니다")
        actions = [a for a in command.follow_up_actions if a.strip()]
        if len(actions) > MAX_FOLLOW_UPS:
            raise ValueError(f"후속조치는 {MAX_FOLLOW_UPS}건까지입니다: {len(actions)}")
        inquiry = command.inquiry_type.strip() if command.inquiry_type and command.inquiry_type.strip() else None
        if inquiry is not None and len(inquiry) > INQUIRY_TYPE_MAX_CHARS:
            raise ValueError(f"유형은 {INQUIRY_TYPE_MAX_CHARS}자까지입니다")

        summary = self._mask(command.summary_text)
        masked_inquiry = self._mask(inquiry) if inquiry is not None else None
        masked_actions = tuple(self._mask(a)[:ACTION_MAX_CHARS] for a in actions)
        revision = await self._revisions.revise(
            command.call_id, summary_text=summary, inquiry_type=masked_inquiry, follow_up_actions=masked_actions,
            reason=self._mask(command.reason)[:REASON_MAX_CHARS],
        )
        return SummaryRevised(call_id=command.call_id, summary_text=summary, inquiry_type=masked_inquiry,
                              follow_up_actions=masked_actions, revision=revision)
