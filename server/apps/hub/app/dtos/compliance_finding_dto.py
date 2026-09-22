# Requirement: C-1, C-2, C-3, C-4
from __future__ import annotations

from dataclasses import dataclass

from .recommendation_card_dto import Source


@dataclass(frozen=True)
class ComplianceFinding:
    """상담원 발화에서 잡힌 위반 1건."""

    rule_code: str  # C-1 ~ C-4 (db: compliance_flag.rule_code)
    phrase: str  # 위반으로 잡힌 표현
    alternative_source: Source | None = None  # 권장 대체 표현 출처 — C-1~C-4 공통 (MANUAL-1.4 및 각 조항, decisions/211)
