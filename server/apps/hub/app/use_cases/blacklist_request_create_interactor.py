# Requirement: J-1, J-2, SEC-1
"""블랙리스트 전환 요청 인터랙터 — 근거를 모으고, 사유를 마스킹하고, `pending` 으로 남긴다.

**여기서 하지 않는 것**:
- 등록하지 않는다. 상태는 늘 `pending` 이다 — 결정은 관리자(`decisions/204`)
- 근거로 점수·등급을 만들지 않는다(부록 A-1). 위기 신호는 차단 사유가 아니라 **경고 표시**다(MANUAL-5.4)
- 클라이언트가 보낸 자막을 쓰지 않는다 — 입력에 자막 필드가 없다(`decisions/205`)
"""

from __future__ import annotations

from hub.app.dtos.blacklist_dto import BlacklistRequest
from hub.app.dtos.blacklist_request_create_dto import BlacklistRequestCreateCommand, BlacklistRequestCreated
from hub.app.ports.input.blacklist_request_create_use_case import BlacklistRequestCreateUseCase
from hub.app.ports.output.blacklist_evidence_port import BlacklistEvidencePort
from hub.app.ports.output.blacklist_port import BlacklistConflict, BlacklistNotFound, BlacklistPort
from hub.app.ports.output.masking_port import MaskingPort

REASON_MAX_CHARS = 500  # `blacklist_request.reason` VARCHAR(500)


class BlacklistRequestCreateInteractor(BlacklistRequestCreateUseCase):
    def __init__(self, blacklist: BlacklistPort, evidence: BlacklistEvidencePort, masking: MaskingPort) -> None:
        self._blacklist = blacklist
        self._evidence = evidence
        self._masking = masking

    async def create(self, command: BlacklistRequestCreateCommand) -> BlacklistRequestCreated:
        if not command.requested_by.strip():
            raise ValueError("요청자(requested_by)가 비어 있습니다")
        if not command.reason.strip():
            raise ValueError("사유가 비어 있습니다")

        collected = await self._evidence.collect(command.call_id)
        if collected is None:
            raise BlacklistNotFound(f"통화가 없습니다: {command.call_id}")
        if collected.customer_ref is None:
            # 누구를 올릴지 모르는 요청을 받지 않는다 — 발신 번호가 안 넘어온 통화다(`decisions/304`)
            raise BlacklistConflict("이 통화는 고객이 식별되지 않았습니다 — 발신 번호 없이 시작된 통화입니다")

        # 사유는 사람이 쓴 자유 문장이라 이름·번호가 섞인다 — 저장 직전에 마스킹한다(`decisions/205`)
        masked_reason, _ = self._masking.mask(command.reason.strip())
        saved = await self._blacklist.save_request(
            BlacklistRequest(
                request_id="",
                call_id=command.call_id,
                customer_ref=collected.customer_ref,
                requested_by=command.requested_by.strip(),
                reason=masked_reason[:REASON_MAX_CHARS],
                context_excerpt=collected.context_excerpt,
                evidence=collected.evidence,
            )
        )
        return BlacklistRequestCreated(request=saved, has_distress=collected.evidence.has_distress)
