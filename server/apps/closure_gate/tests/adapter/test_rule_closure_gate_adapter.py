# Requirement: F-2, QUA-1
"""어댑터는 도메인 판정을 허브 DTO 로 옮기기만 한다 — 규칙표 서류만 싣고, 근거 조항을 붙인다."""

import pytest

from closure_gate.adapter.outbound.keyword_required_docs_detection_adapter import KeywordRequiredDocsDetectionAdapter
from closure_gate.adapter.outbound.rule_closure_gate_adapter import SUPPORTED_PROCEDURES, RuleClosureGateAdapter
from closure_gate.domain.services.gate import UnknownProcedure
from hub.app.ports.output import ClosureGatePort


def test_포트를_구현한다():
    assert isinstance(RuleClosureGateAdapter(), ClosureGatePort)


def test_규칙표_서류만_싣고_근거_조항과_조건부_서류를_붙인다():
    v = RuleClosureGateAdapter().evaluate("c1", "DASAN-TERM-4.3", {"신분증": False, "엉뚱한키": True}, reason="r")
    assert v.verdict == "incomplete" and v.missing == ("신분증",)
    assert v.evidence == {"신분증": False}
    assert v.source.doc_id == "DASAN-TERM-4.3" and v.procedure_title == "주민등록초본 발급"
    assert v.conditional and v.detected is False and v.reason == "r"


def test_지원하는_절차는_25개다():
    assert len(SUPPORTED_PROCEDURES) == 25


def test_자동_판정_어댑터는_규칙_없는_절차를_거절한다():
    with pytest.raises(UnknownProcedure):
        KeywordRequiredDocsDetectionAdapter().detect("DASAN-TERM-2.6", ("신분증",))
