# Requirement: F-2, QUA-1
"""스텁 포트로 배선만 검증. 판정 규칙은 closure_gate 스포크의 domain/services 가 소유한다."""

import asyncio

import pytest

from hub.app.dtos import ClosureVerdict
from hub.app.dtos.closure_dto import ClosureCheckCommand
from hub.app.ports.output import ClosureGatePort
from hub.app.ports.output.closure_record_port import ClosureRecordPort
from hub.app.use_cases.closure_check_interactor import ClosureCheckInteractor

EVIDENCE = {"신고서": True, "신고인 신분증": False}


class _Spy(ClosureGatePort):
    def __init__(self):
        self.calls = []

    def evaluate(self, call_id, procedure, evidence, reason=None):
        self.calls.append((call_id, procedure, dict(evidence), reason))
        missing = tuple(k for k, v in evidence.items() if not v)
        return ClosureVerdict(call_id=call_id, procedure=procedure, evidence=dict(evidence),
                              verdict="incomplete" if missing else "complete", missing=missing, reason=reason)


class _Record(ClosureRecordPort):
    def __init__(self):
        self.verdicts = []

    async def record(self, verdict):
        self.verdicts.append(verdict)


def _run(port, evidence=None, procedure="DASAN-TERM-4.4", record=None):
    cmd = ClosureCheckCommand(call_id="c_001", procedure=procedure,
                              evidence=EVIDENCE if evidence is None else evidence, reason="안내 완료")
    return asyncio.run(ClosureCheckInteractor(closure_gate=port, record=record).check(cmd))


def test_포트에_그대로_넘기고_판정을_남긴다():
    port, record = _Spy(), _Record()
    verdict = _run(port, record=record)
    assert port.calls[0] == ("c_001", "DASAN-TERM-4.4", EVIDENCE, "안내 완료")
    assert record.verdicts == [verdict]


def test_허브가_판정하지_않는다():
    verdict = _run(_Spy())
    assert verdict.verdict == "incomplete" and verdict.missing == ("신고인 신분증",)


def test_빈_근거는_거부한다():
    port = _Spy()
    with pytest.raises(ValueError):
        _run(port, {})
    assert port.calls == []


def test_절차가_비면_거부한다():
    port = _Spy()
    with pytest.raises(ValueError):
        _run(port, procedure="")
    assert port.calls == []


def test_evidence를_복사해_넘긴다():
    port = _Spy()
    evidence = {"신고서": True}
    asyncio.run(ClosureCheckInteractor(closure_gate=port).check(
        ClosureCheckCommand(call_id="c", procedure="DASAN-TERM-4.4", evidence=evidence)))
    evidence["신고서"] = False
    assert port.calls[0][2] == {"신고서": True}
