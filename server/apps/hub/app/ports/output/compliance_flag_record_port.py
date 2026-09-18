# Requirement: C-1, C-2, C-3, C-4, D-4
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.compliance_finding_dto import ComplianceFinding


class ComplianceFlagRecordPort(ABC):
    """잡힌 컴플라이언스 위반(C-1~C-4)을 남긴다. append-only — D-4 「놓친 위반 표현 누적」의 원천이다.

    `findings` 의 `phrase` 는 **마스킹된 상담원 발화 기준**이어야 한다(콜 미디에이터가 마스킹본을 보낸다).
    원문을 받는 시그니처를 두지 않는다. 검사 응답은 저장과 무관하게 나간다 — 저장이 실패해도 인터랙터가
    응답을 막지 않는다(로그만 남긴다).
    """

    @abstractmethod
    async def record(self, call_id: str, segment_id: int, findings: tuple[ComplianceFinding, ...]) -> None: ...
