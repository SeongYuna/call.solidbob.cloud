# Requirement: C-1, C-2, C-3, C-4, D-4, QUA-1
"""스텁 포트로 배선만 검증. 실제 탐지 성능(재현율 ≥0.90)은 compliance 스포크가 골든셋으로 채점받는다."""

import asyncio

import pytest

from hub.app.dtos import ComplianceFinding, Source
from hub.app.dtos.compliance_dto import ComplianceCheckCommand
from hub.app.ports.output import CompliancePort
from hub.app.ports.output.compliance_flag_record_port import ComplianceFlagRecordPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.app.use_cases.compliance_check_interactor import ComplianceCheckInteractor

FINDING = ComplianceFinding(rule_code="C-1", phrase="무조건 보장됩니다",
                            alternative_source=Source(doc_id="FIN-MANUAL-1.4", title="응대 매뉴얼 1.4"))


class _Spy(CompliancePort):
    def __init__(self, findings=None):
        self.findings = [] if findings is None else findings
        self.calls = []

    async def detect(self, agent_utterance):
        self.calls.append(agent_utterance)
        return list(self.findings)


class _Record(ComplianceFlagRecordPort):
    def __init__(self, fail_with=None):
        self.calls = []
        self._fail_with = fail_with

    async def record(self, call_id, segment_id, findings):
        self.calls.append((call_id, segment_id, findings))
        if self._fail_with is not None:
            raise self._fail_with


def _run(port, utterance="무조건 보장됩니다", record=None):
    cmd = ComplianceCheckCommand(call_id="c_001", segment_id=7, agent_utterance=utterance)
    return asyncio.run(ComplianceCheckInteractor(compliance=port, record=record or _Record()).check(cmd))


def test_상담원_발화를_포트에_그대로_넘긴다():
    port = _Spy([FINDING])
    _run(port)
    assert port.calls == ["무조건 보장됩니다"]


def test_잡힌_위반을_그대로_싣는다():
    result = _run(_Spy([FINDING]))
    assert result.findings[0].rule_code == "C-1"
    assert result.findings[0].alternative_source.doc_id == "FIN-MANUAL-1.4"


def test_통화와_발화_식별자를_유지한다():
    result = _run(_Spy([FINDING]))
    assert (result.call_id, result.segment_id) == ("c_001", 7)


def test_잡힌_위반을_기록_포트에_남긴다():
    """D-4 「놓친 위반 표현 누적」의 원천 — 검사 결과가 응답으로만 나가고 사라지면 안 된다(2026-09-18 전까지 그랬다)."""
    record = _Record()
    _run(_Spy([FINDING]), record=record)
    assert record.calls == [("c_001", 7, (FINDING,))]


def test_발견이_없으면_기록하지_않고_빈_목록이다():
    """'잡힌 것이 없음'이지 '안전함'이 아니다 — 등급·점수를 만들지 않는다 (부록 A-1)."""
    record = _Record()
    result = _run(_Spy([]), record=record)
    assert result.findings == ()
    assert result.has_findings is False
    assert record.calls == []
    # 응답 DTO 어디에도 안전·위험도 필드가 없다
    assert not hasattr(result, "risk_score")
    assert not hasattr(result, "safe")


@pytest.mark.parametrize("failure", [CallNotStartedError("c_001"), RuntimeError("db down")])
def test_저장이_실패해도_응답은_그대로_나간다(failure):
    """전사가 아직 없거나(외래키) DB 가 죽어도 화면 경고가 먼저다 — 저장 실패는 로그로만."""
    record = _Record(fail_with=failure)
    result = _run(_Spy([FINDING]), record=record)
    assert result.findings == (FINDING,)
    assert len(record.calls) == 1


def test_애매한_건을_허브가_걸러내지_않는다():
    """재현율 우선 — 판단은 스포크가 하고 허브는 나른다."""
    many = [FINDING, ComplianceFinding(rule_code="C-3", phrase="따로 고지 안 해도 됩니다")]
    assert len(_run(_Spy(many)).findings) == 2


@pytest.mark.parametrize("utterance", ["", "   "])
def test_빈_발화는_거부한다(utterance):
    port = _Spy([FINDING])
    record = _Record()
    with pytest.raises(ValueError):
        _run(port, utterance, record=record)
    assert port.calls == []
    assert record.calls == []
