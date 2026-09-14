# Requirement: C-6
"""`CallGuardPort` 구현 — 규칙 판정을 hub 계약(`CallGuardFlag`)으로 옮긴다.

여기가 adapter 인 이유: hub 의 DTO 를 아는 코드이기 때문이다. 판정 자체는
`domain/services/detector.py` 에 있고 이 파일은 형태만 바꾼다(`.importlinter` 계약 1).
"""

from __future__ import annotations

from hub.app.dtos.call_guard_dto import CallGuardFlag
from hub.app.ports.output.call_guard_port import CallGuardPort

from ...domain.services.detector import detect


class RuleCallGuardAdapter(CallGuardPort):
    """규칙 기반 v1. 분류기가 붙으면 이 어댑터를 갈아끼운다.

    ⚠ **`phrase` 는 이미 마스킹된 자막에서 잘라낸 것이어야 한다**(`DASAN-MANUAL-5.5`).
    이 어댑터는 받은 문자열을 그대로 자르므로, **호출하는 쪽이 C-5 뒤에 두어야 한다.**
    파이프라인 순서가 바뀌면 폭언 기록에 개인정보가 남는다 — 여기서는 막을 수 없다.
    """

    async def detect(self, customer_utterance: str) -> list[CallGuardFlag]:
        return [
            CallGuardFlag(
                category=d.category,
                phrase=d.phrase,
                source_doc_id=d.source_doc_id,
            )
            for d in detect(customer_utterance)
        ]
