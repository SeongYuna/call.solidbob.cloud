# Requirement: C-1, C-2, C-3, C-4
"""`CompliancePort` 구현 — 규칙 판정을 hub 계약(`ComplianceFinding`)으로 옮긴다.

판정은 `domain/services/detector.py` 가 한다. 여기는 형태만 바꾼다(`.importlinter` 계약 1).
**응답 필드는 `rule_code`·`phrase`·`alternative_source` 뿐이다** — 등급·점수를 계산해도 실어 보낼 자리가 없고, 만들지 않는다(부록 A-1).

⚠ 대체 표현 출처의 **제목은 조항 ID 로 둔다.** 조항 제목을 여기 옮겨 적으면 지식베이스와 두 벌이 된다 — 화면이 조항 ID 로 본문을 찾는다.
⚠ 규칙 v1 이다. 분류기(KcELECTRA, 기획서 2.4절)가 오면 이 어댑터를 갈아끼운다.
"""

from __future__ import annotations

from hub.app.dtos.compliance_finding_dto import ComplianceFinding
from hub.app.dtos.recommendation_card_dto import Source
from hub.app.ports.output.compliance_port import CompliancePort

from ...domain.services.detector import detect


class RuleComplianceAdapter(CompliancePort):
    async def detect(self, agent_utterance: str) -> list[ComplianceFinding]:
        return [
            ComplianceFinding(
                rule_code=d.code,
                phrase=d.phrase,
                alternative_source=Source(doc_id=d.alternative_doc_id, title=d.alternative_doc_id),
            )
            for d in detect(agent_utterance)
        ]
