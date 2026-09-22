# Requirement: D-1, D-2, D-3, D-6, SEC-1
"""통화 후 처리 인터랙터. PostcallPort 를 부르고 초안 성격을 지킨 채 기록 포트에 남기는 것이 전부다.

**여기서 하지 않는 것**:
- 유형(D-2)을 확정하지 않는다. 모델이 무엇을 주든 `confirmed=False` 로 내보낸다 —
  확정은 상담원이 화면에서 한다(부록 A-1).
- 요약을 다시 다듬지 않는다. 손대면 모델 출력과 화면 표시가 달라져 환각 추적이 끊긴다.
- 원문을 다루지 않는다. 받는 것도 돌려주는 것도 마스킹 완료본뿐이다 (SEC-1).
- 확정된 요약을 덮을지 판단하지 않는다 — 기록 포트가 `SummaryAlreadyConfirmedError` 로 막는다(w7-postcall-persistence).
"""

from __future__ import annotations

from dataclasses import replace

from hub.app.dtos.call_summary_dto import CallSummaryDraft
from hub.app.dtos.postcall_dto import PostcallCommand
from hub.app.ports.input.postcall_use_case import PostcallUseCase
from hub.app.ports.output.postcall_port import PostcallPort
from hub.app.ports.output.postcall_record_port import PostcallRecordPort


class PostcallInteractor(PostcallUseCase):
    def __init__(self, postcall: PostcallPort, record: PostcallRecordPort) -> None:
        self._postcall = postcall
        self._record = record

    async def close(self, command: PostcallCommand) -> CallSummaryDraft:
        if not command.segments:
            raise ValueError("전사가 비어 있습니다 — 요약할 내용이 없습니다")

        draft = await self._postcall.summarize(command.call_id, list(command.segments))
        # 모델이 confirmed=True 를 실어 보내도 무시한다 — 확정은 사람이 하는 일이다
        draft = replace(draft, call_id=command.call_id, confirmed=False)
        await self._record.record(draft)  # 저장한 것과 돌려주는 것이 같은 초안이다
        return draft
