# Requirement: D-4
"""공백 신고 인터랙터. 검증하고 저장하는 것이 전부다.

**신고를 걸러내지 않는다.** 중복이든 애매하든 그대로 받는다 — 무엇이 공백인지 판단하는 것은
집계 단계(`ai/`)의 일이고, 입구에서 거르면 그 판단의 재료가 사라진다.
"""

from __future__ import annotations

from hub.app.dtos.knowledge_gap_dto import KnowledgeGapReceipt, KnowledgeGapReport
from hub.app.ports.input.knowledge_gap_use_case import KnowledgeGapUseCase
from hub.app.ports.output.knowledge_gap_port import KnowledgeGapPort
from hub.app.ports.output.masking_port import MaskingPort

MAX_DESCRIPTION = 300  # db `knowledge_gap.description` VARCHAR(300)


class KnowledgeGapInteractor(KnowledgeGapUseCase):
    def __init__(self, gaps: KnowledgeGapPort, masking: MaskingPort | None = None) -> None:
        self._gaps = gaps
        # 상담원이 자유롭게 쓰는 칸이라 번호가 들어올 수 있다 — 저장 전에 가린다(C-5·SEC-1, `decisions/322`)
        self._masking = masking

    async def report(self, report: KnowledgeGapReport) -> KnowledgeGapReceipt:
        description = report.description.strip()
        if not description:
            raise ValueError("무엇을 못 찾았는지 적어야 합니다")
        if len(description) > MAX_DESCRIPTION:
            raise ValueError(f"설명은 {MAX_DESCRIPTION}자 이내여야 합니다: {len(description)}자")

        gap_id = await self._gaps.save(
            KnowledgeGapReport(
                module=report.module,
                description=self._masking.mask(description)[0] if self._masking else description,
                call_id=report.call_id,
                segment_id=report.segment_id,
                closure_id=report.closure_id,
            )
        )
        return KnowledgeGapReceipt(gap_id=gap_id, module=report.module)
