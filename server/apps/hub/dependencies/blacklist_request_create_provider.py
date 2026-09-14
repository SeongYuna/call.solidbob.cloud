# Requirement: J-1, J-2
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.blacklist_request_create_use_case import BlacklistRequestCreateUseCase
from hub.app.ports.output.blacklist_evidence_port import BlacklistEvidencePort
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.use_cases.blacklist_request_create_interactor import BlacklistRequestCreateInteractor
from hub.dependencies.blacklist_provider import get_blacklist_evidence_port, get_blacklist_port
from hub.dependencies.masking_provider import get_masking_port


def get_blacklist_request_create_use_case(
    blacklist: BlacklistPort = Depends(get_blacklist_port),
    evidence: BlacklistEvidencePort = Depends(get_blacklist_evidence_port),
    masking: MaskingPort = Depends(get_masking_port),
) -> BlacklistRequestCreateUseCase:
    return BlacklistRequestCreateInteractor(blacklist=blacklist, evidence=evidence, masking=masking)
