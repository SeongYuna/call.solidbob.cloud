# Requirement: J-4
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.blacklist_retention_purge_use_case import BlacklistRetentionPurgeUseCase
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.use_cases.blacklist_retention_purge_interactor import BlacklistRetentionPurgeInteractor
from hub.dependencies.blacklist_provider import get_blacklist_port


def get_blacklist_retention_purge_use_case(
    blacklist: BlacklistPort = Depends(get_blacklist_port),
) -> BlacklistRetentionPurgeUseCase:
    return BlacklistRetentionPurgeInteractor(blacklist=blacklist)
