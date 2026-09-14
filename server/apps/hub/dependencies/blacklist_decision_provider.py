# Requirement: J-4
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.blacklist_decision_use_case import BlacklistDecisionUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.use_cases.blacklist_decision_interactor import BlacklistDecisionInteractor
from hub.dependencies.blacklist_provider import get_blacklist_port
from hub.dependencies.masking_provider import get_masking_port


def get_blacklist_decision_use_case(
    blacklist: BlacklistPort = Depends(get_blacklist_port),
    masking: MaskingPort = Depends(get_masking_port),
) -> BlacklistDecisionUseCase:
    return BlacklistDecisionInteractor(blacklist=blacklist, masking=masking)
