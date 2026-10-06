# Requirement: D-1, D-2, D-3, D-6, SEC-1
"""통화 후 처리 인터랙터. PostcallPort 를 부르고 초안 성격을 지킨 채 기록 포트에 남기는 것이 전부다.

**여기서 하지 않는 것**:
- 유형(D-2)을 확정하지 않는다. 모델이 무엇을 주든 `confirmed=False` 로 내보낸다 —
  확정은 상담원이 화면에서 한다(부록 A-1).
- 요약을 다시 다듬지 않는다. 손대면 모델 출력과 화면 표시가 달라져 환각 추적이 끊긴다.
- 원문을 요약·저장으로 넘기지 않는다. 받는 자막은 화면이 들고 있던 것이라 **원문일 수 있어서**(`decisions/326`)
  요약하기 전에 MaskingPort 로 가린다 — 요약 포트·기록 포트·응답에는 마스킹 완료본만 간다 (SEC-1).
- 확정된 요약을 덮을지 판단하지 않는다 — 기록 포트가 `SummaryAlreadyConfirmedError` 로 막는다(w7-postcall-persistence).
"""

from __future__ import annotations

from dataclasses import replace

from hub.app.dtos.call_summary_dto import CallSummaryDraft
from hub.app.dtos.postcall_dto import PostcallCommand, PostcallSegment
from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.input.postcall_use_case import PostcallUseCase
from hub.app.ports.output.compliance_flag_query_port import ComplianceFlagQueryPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.postcall_port import PostcallPort
from hub.app.ports.output.postcall_record_port import PostcallRecordPort


class PostcallInteractor(PostcallUseCase):
    def __init__(
        self,
        postcall: PostcallPort,
        record: PostcallRecordPort,
        masking: MaskingPort,
        flags: ComplianceFlagQueryPort | None = None,
    ) -> None:
        self._postcall = postcall
        self._record = record
        self._masking = masking
        self._flags = flags

    def _masked(self, call_id: str, segment: PostcallSegment) -> TranscriptEvent:
        text, spans = self._masking.mask(segment.raw_text)
        return TranscriptEvent(
            call_id=call_id,
            segment_id=segment.segment_id,
            speaker=segment.speaker,
            text=text,
            is_final=segment.is_final,
            utterance_end_ms=segment.utterance_end_ms,
            masked=tuple(spans),
        )

    async def close(self, command: PostcallCommand) -> CallSummaryDraft:
        if not command.segments:
            raise ValueError("전사가 비어 있습니다 — 요약할 내용이 없습니다")

        # 위반이 잡힌 상담원 발화는 「안내」로 발췌되지 않게 번호를 같이 넘긴다(2026-10-01). 읽기 실패는 요약을 막지 않는다
        flagged: frozenset[int] = frozenset()
        if self._flags is not None:
            try:
                flagged = await self._flags.flagged_segment_ids(command.call_id)
            except Exception:  # noqa: BLE001 — 저장 조회가 죽어도 초안은 낸다(전과 같은 초안)
                flagged = frozenset()
        # 화면 자막은 원문일 수 있다 — 요약(모델 포함)에 넘기기 전에 가린다. 요약에는 지금까지와 같은 마스킹본이 간다
        segments = [self._masked(command.call_id, s) for s in command.segments]
        draft = await self._postcall.summarize_with_flags(command.call_id, segments, flagged)
        # 모델이 confirmed=True 를 실어 보내도 무시한다 — 확정은 사람이 하는 일이다
        draft = replace(draft, call_id=command.call_id, confirmed=False)
        await self._record.record(draft)  # 저장한 것과 돌려주는 것이 같은 초안이다
        return draft
