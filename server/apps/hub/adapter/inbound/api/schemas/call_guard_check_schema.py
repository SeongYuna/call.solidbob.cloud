# Requirement: C-6
"""HTTP 표면 스키마. 필드명은 db `call_guard_flag` 를 따르고, 응답 값은 전부 문자열이다(`_types.StrField`)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField


class CallGuardCheckRequest(BaseModel):
    call_id: str
    segment_id: int = Field(description="정수 또는 숫자 문자열('12')")
    customer_utterance: str = Field(min_length=1, description="**마스킹된** 고객 발화만. 상담원 발화는 검사하지 않는다")


class CallGuardFlagSchema(BaseModel):
    category: str = Field(description="insult · threat · sexual · distress — distress 는 대응이 반대다(MANUAL-5.4)")
    phrase: str = Field(description="잡힌 표현 — 마스킹된 발화에서 잘라낸 것")
    span: list[StrField] = Field(description="[start, end) 문자 오프셋 — 마스킹된 발화 기준")
    source_doc_id: str | None = Field(default=None, description="근거 조항 (DASAN-MANUAL-5.x)")


class CallGuardCheckResponse(BaseModel):
    call_id: str
    segment_id: StrField
    flags: list[CallGuardFlagSchema] = Field(
        description="빈 배열은 '잡힌 것이 없음'이지 '안전함'이 아니다 (부록 A-1)"
    )
