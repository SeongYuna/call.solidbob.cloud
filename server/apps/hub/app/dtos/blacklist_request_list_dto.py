# Requirement: J-4
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlacklistRequestListQuery:
    status: str | None = None  # pending · approved · rejected. None 이면 전부
