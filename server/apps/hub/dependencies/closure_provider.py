# Requirement: F-2
"""ClosureGatePort 프로바이더. 규칙 기반 게이트가 기본이다 — 필요서류 체크리스트(`decisions/305`).

**규칙표는 다산 필요서류 조항(`DASAN-TERM-*`)이 소유한다.** 이 프로바이더도, 허브도 어떤 서류가 필수인지 모른다.
"""

from __future__ import annotations

from closure_gate.adapter.outbound.rule_closure_gate_adapter import RuleClosureGateAdapter
from fastapi import Depends

from hub.app.ports.input.closure_check_use_case import ClosureCheckUseCase
from hub.app.ports.output.closure_gate_port import ClosureGatePort
from hub.app.ports.output.closure_record_port import ClosureRecordPort
from hub.app.use_cases.closure_check_interactor import ClosureCheckInteractor
from hub.dependencies.closure_record_provider import get_closure_record_port


def get_closure_gate_port() -> ClosureGatePort:
    return RuleClosureGateAdapter()


def get_closure_check_use_case(
    closure_gate: ClosureGatePort = Depends(get_closure_gate_port),
    record: ClosureRecordPort = Depends(get_closure_record_port),
) -> ClosureCheckUseCase:
    return ClosureCheckInteractor(closure_gate=closure_gate, record=record)
