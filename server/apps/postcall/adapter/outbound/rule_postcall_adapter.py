# Requirement: D-1, D-2, D-3, SEC-1
"""PostcallPort 구현 — 허브 계약과 postcall 도메인 규칙을 잇는다 (`decisions/306`).

허브 DTO → 도메인 발화로 옮기고, 결과를 `CallSummaryDraft` 로 되돌리는 것이 전부다.
**초안을 만드는 것은 도메인이다** — 이 어댑터에는 발췌·약속 판정이 없다.
interim 은 버린다(7.3절 — 화면 갱신용이고 확정본이 아니다).
"""

from __future__ import annotations

from hub.app.dtos.call_summary_dto import CallSummaryDraft, FollowUpAction
from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.output.postcall_port import PostcallPort

from ...domain.services.summary_rules import Utterance, build_draft


class RulePostcallAdapter(PostcallPort):
    async def summarize(self, call_id: str, segments: list[TranscriptEvent]) -> CallSummaryDraft:
        finals = sorted((s for s in segments if s.is_final), key=lambda s: s.segment_id)
        parts = build_draft([Utterance(speaker=s.speaker, text=s.text) for s in finals])
        return CallSummaryDraft(
            call_id=call_id,
            summary_text=parts.summary_text,
            inquiry_type=parts.inquiry_type,
            follow_up_actions=tuple(FollowUpAction(action_text=a) for a in parts.follow_up_actions),
            confirmed=False,
        )
