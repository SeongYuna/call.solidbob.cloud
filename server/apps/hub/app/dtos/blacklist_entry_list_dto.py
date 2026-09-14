# Requirement: J-4
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlacklistEntryListQuery:
    active_only: bool = False  # True 면 해제·만료되지 않은 것만. 기본은 전부 — 재범 판단에 옛 에피소드가 필요하다
