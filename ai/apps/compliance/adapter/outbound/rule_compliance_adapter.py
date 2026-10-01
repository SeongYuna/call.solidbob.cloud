# Requirement: C-1, C-2, C-3, C-4
"""`CompliancePort` 구현 — 규칙 판정을 hub 계약(`ComplianceFinding`)으로 옮긴다.

판정은 `domain/services/detector.py` 가 한다. 여기는 형태만 바꾼다(`.importlinter` 계약 1).
**응답 필드는 `rule_code`·`phrase`·`alternative_source` 뿐이다** — 등급·점수를 계산해도 실어 보낼 자리가 없고, 만들지 않는다(부록 A-1).

⚠ 대체 표현 출처의 **제목은 매뉴얼의 권장 문장이다**(2026-10-02) — 화면이 `title` 을 그대로 「권장 표현」 자리에 띄운다.
  조항에 문장이 없는 갈래는 전처럼 **조항 ID** 를 둔다(화면이 「근거 조항」으로 가른다). 조항 제목을 옮겨 적지 않는 것은 그대로다.
⚠ 규칙 v1 이다. 분류기(KcELECTRA, 기획서 2.4절)가 오면 이 어댑터를 갈아끼운다.
"""

from __future__ import annotations

from hub.app.dtos.compliance_finding_dto import ComplianceFinding
from hub.app.dtos.recommendation_card_dto import Source
from hub.app.ports.output.compliance_port import CompliancePort

from ...domain.services.detector import Detection, detect

# MANUAL.md 머리말이 정한 인용 이름 — 화면·리포트에는 이 문서를 「민원응대매뉴얼」로 부른다
_MANUAL_NAME = "민원응대매뉴얼"


def _title(d: Detection) -> str:
    """권장 문장 뒤에 조항 번호를 붙인다 — 문장만 보내면 화면에서 근거가 사라진다."""
    if d.alternative_phrase is None:
        return d.alternative_doc_id
    clause = d.alternative_doc_id.rsplit("-", 1)[-1]  # DASAN-MANUAL-1.4 → 1.4
    return f"{d.alternative_phrase} ({_MANUAL_NAME} {clause})"


class RuleComplianceAdapter(CompliancePort):
    async def detect(self, agent_utterance: str) -> list[ComplianceFinding]:
        return [
            ComplianceFinding(
                rule_code=d.code,
                phrase=d.phrase,
                alternative_source=Source(doc_id=d.alternative_doc_id, title=_title(d)),
            )
            for d in detect(agent_utterance)
        ]
