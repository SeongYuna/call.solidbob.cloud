# Requirement: D-4
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ._types import StrField


class KnowledgeGapRequest(BaseModel):
    module: Literal["B", "C", "F"] = Field(
        description="B 검색 실패 · C 놓친 위반 · F 통과했으나 사후 문제 (2.5절 D-4 확장)"
    )
    description: str = Field(min_length=1, max_length=300, description="무엇을 못 찾았는지")
    call_id: str | None = None
    segment_id: int | None = None
    closure_id: int | None = None


class KnowledgeGapResponse(BaseModel):
    gap_id: StrField
    module: Literal["B", "C", "F"]
