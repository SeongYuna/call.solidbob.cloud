# Requirement: C-6
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.call_guard_check_use_case import CallGuardCheckUseCase
from hub.app.ports.output.call_guard_flag_record_port import CallGuardFlagRecordPort
from hub.app.ports.output.call_guard_port import CallGuardPort
from hub.app.use_cases.call_guard_check_interactor import CallGuardCheckInteractor
from hub.dependencies.call_guard_flag_record_provider import get_call_guard_flag_record_port
from hub.dependencies.call_guard_provider import get_call_guard_port


def get_call_guard_check_use_case(
    call_guard: CallGuardPort = Depends(get_call_guard_port),
    record: CallGuardFlagRecordPort = Depends(get_call_guard_flag_record_port),
) -> CallGuardCheckUseCase:
    return CallGuardCheckInteractor(call_guard=call_guard, record=record)
