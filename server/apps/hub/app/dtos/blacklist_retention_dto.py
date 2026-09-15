# Requirement: J-4, SEC-1
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RetentionPurgeResult:
    """보존 기간 정리 한 번의 결과 — 몇 건의 문장을 비웠는가(`decisions/312`). 행 수가 아니라 비운 행 수다."""

    retention_days: int
    cutoff: datetime  # 이 시각 이전에 끝난 것만 비웠다
    expiry_change_reasons_purged: int
    rejected_requests_purged: int
