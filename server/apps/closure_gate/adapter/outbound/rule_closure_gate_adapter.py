# Requirement: F-2
"""ClosureGatePort 구현 — 허브 계약과 closure_gate 도메인을 잇는다.

도메인의 `GateDecision` 을 허브 DTO `ClosureVerdict` 로 옮기는 것이 전부다.
**판정은 도메인이 한다** — 이 어댑터에는 `if evidence[...]` 가 없다(절대 원칙 9).
"""

from __future__ import annotations

from hub.app.dtos.closure_verdict_dto import ClosureVerdict
from hub.app.dtos.recommendation_card_dto import Source
from hub.app.ports.output.closure_gate_port import ClosureGatePort

from ...domain.services.gate import evaluate

# 이 어댑터가 판정할 수 있는 절차. 평가 하네스가 "무엇을 못 보는지" 알아야 한다.
from ...domain.value_objects.closure_rule import RULES

SUPPORTED_PROCEDURES = tuple(RULES)


class RuleClosureGateAdapter(ClosureGatePort):
    def evaluate(
        self, call_id: str, procedure: str, evidence: dict[str, bool], reason: str | None = None
    ) -> ClosureVerdict:
        decision = evaluate(procedure, evidence)
        rule = decision.rule
        return ClosureVerdict(
            call_id=call_id,
            procedure=procedure,
            procedure_title=rule.title,
            # 규칙표의 서류만 싣는다 — 호출자가 보낸 엉뚱한 키는 판정에 쓰이지 않았으므로 되돌려 주지 않는다
            evidence={doc.name: evidence.get(doc.name) is True for doc in rule.required},
            verdict=decision.verdict,
            missing=decision.missing,
            reason=reason,
            source=Source(doc_id=rule.procedure, title=f"{rule.title} — 필요서류"),
            conditional=rule.conditional,
        )
