# Requirement: C-1, C-2, C-3, C-4
"""CompliancePort 프로바이더. 스포크가 없으면 501 — 빈 목록을 돌려주지 않는다.

빈 목록은 "위반이 없다"로 읽힌다. 분류기가 아예 없는 상태를 그렇게 보고하면 **탐지가 죽은 것을
'깨끗하다'로 오해**하게 만든다. 재현율 우선(애매하면 잡는다) 원칙과 정반대 방향의 사고다.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from hub.app.ports.input.compliance_check_use_case import ComplianceCheckUseCase
from hub.app.ports.output.compliance_flag_record_port import ComplianceFlagRecordPort
from hub.app.ports.output.compliance_port import CompliancePort
from hub.app.use_cases.compliance_check_interactor import ComplianceCheckInteractor
from hub.dependencies.compliance_flag_record_provider import get_compliance_flag_record_port


def get_compliance_port() -> CompliancePort:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="compliance 스포크가 등록되지 않았습니다 (C-1~C-4)",
    )


def get_compliance_check_use_case(
    compliance: CompliancePort = Depends(get_compliance_port),
    record: ComplianceFlagRecordPort = Depends(get_compliance_flag_record_port),
) -> ComplianceCheckUseCase:
    return ComplianceCheckInteractor(compliance=compliance, record=record)
