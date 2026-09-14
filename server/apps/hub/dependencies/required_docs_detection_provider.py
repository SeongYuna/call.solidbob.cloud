# Requirement: F-2
from __future__ import annotations

from closure_gate.adapter.outbound.keyword_required_docs_detection_adapter import KeywordRequiredDocsDetectionAdapter
from fastapi import Depends

from hub.app.ports.input.required_docs_detection_use_case import RequiredDocsDetectionUseCase
from hub.app.ports.output.closure_gate_port import ClosureGatePort
from hub.app.ports.output.closure_record_port import ClosureRecordPort
from hub.app.ports.output.required_docs_detection_port import RequiredDocsDetectionPort
from hub.app.use_cases.required_docs_detection_interactor import RequiredDocsDetectionInteractor
from hub.dependencies.closure_provider import get_closure_gate_port
from hub.dependencies.closure_record_provider import get_closure_record_port


def get_required_docs_detection_port() -> RequiredDocsDetectionPort:
    return KeywordRequiredDocsDetectionAdapter()


def get_required_docs_detection_use_case(
    detection: RequiredDocsDetectionPort = Depends(get_required_docs_detection_port),
    closure_gate: ClosureGatePort = Depends(get_closure_gate_port),
    record: ClosureRecordPort = Depends(get_closure_record_port),
) -> RequiredDocsDetectionUseCase:
    return RequiredDocsDetectionInteractor(detection=detection, closure_gate=closure_gate, record=record)
