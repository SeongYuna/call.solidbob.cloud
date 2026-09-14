# Requirement: F-2, QUA-1
"""자동 판정 인터랙터 — 탐지 → 게이트 → 기록 순서와 `detected=True` 표시만 본다."""

import asyncio

from hub.app.dtos import ClosureVerdict
from hub.app.dtos.required_docs_detection_dto import RequiredDocsDetectionCommand
from hub.app.ports.output import ClosureGatePort
from hub.app.ports.output.closure_record_port import ClosureRecordPort
from hub.app.ports.output.required_docs_detection_port import RequiredDocsDetectionPort
from hub.app.use_cases.required_docs_detection_interactor import RequiredDocsDetectionInteractor


class _Detect(RequiredDocsDetectionPort):
    def __init__(self):
        self.calls = []

    def detect(self, procedure, agent_utterances):
        self.calls.append((procedure, agent_utterances))
        return {"신고서": True, "신고인 신분증": False}


class _Gate(ClosureGatePort):
    def __init__(self):
        self.evidence = None

    def evaluate(self, call_id, procedure, evidence, reason=None):
        self.evidence = evidence
        return ClosureVerdict(call_id=call_id, procedure=procedure, evidence=evidence, verdict="incomplete",
                              missing=("신고인 신분증",))


class _Record(ClosureRecordPort):
    def __init__(self):
        self.verdicts = []

    async def record(self, verdict):
        self.verdicts.append(verdict)


def test_탐지한_근거로_판정하고_자동_판정_표시를_붙여_남긴다():
    detect, gate, record = _Detect(), _Gate(), _Record()
    cmd = RequiredDocsDetectionCommand(call_id="c1", procedure="DASAN-TERM-4.4", agent_utterances=("신고서 준비하세요",))
    verdict = asyncio.run(RequiredDocsDetectionInteractor(detect, gate, record).check(cmd))
    assert detect.calls == [("DASAN-TERM-4.4", ("신고서 준비하세요",))]
    assert gate.evidence == {"신고서": True, "신고인 신분증": False}
    assert verdict.detected is True and record.verdicts == [verdict]
