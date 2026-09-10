# Requirement: 7.3절 전사 이벤트
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.call_start_use_case import CallStartUseCase
from hub.app.ports.output.call_start_record_port import CallStartRecordPort
from hub.app.use_cases.call_start_interactor import CallStartInteractor
from hub.dependencies.call_record_provider import get_call_record_port


def get_call_start_use_case(
    record: CallStartRecordPort = Depends(get_call_record_port),
) -> CallStartUseCase:
    return CallStartInteractor(record=record)
