# Requirement: J-1, J-2
from __future__ import annotations

from dataclasses import dataclass

from .blacklist_dto import BlacklistRequest, RequestEvidence


@dataclass(frozen=True)
class BlacklistRequestCreateCommand:
    """상담원의 전환 요청. **근거·고객·자막은 받지 않는다** — 서버가 `call_id` 로 DB 에서 모은다(`decisions/205`).

    클라이언트가 자막을 보내게 두면 원문이 들어갈 입력이 생긴다. `reason` 만 사람이 쓰고, 저장 전에 마스킹한다.
    """

    call_id: str
    requested_by: str  # agent.agent_id — 상담원 토큰에서 온다(`decisions/307`). 본문으로 받지 않는다
    reason: str


@dataclass(frozen=True)
class CallEvidence:
    """한 통화에서 모은 근거. 전부 건수·시간이다 — 점수를 만들지 않는다(부록 A-1)."""

    customer_ref: str | None  # `call.customer_id` — 발신 번호가 안 넘어온 통화면 None
    evidence: RequestEvidence
    context_excerpt: str  # 마스킹된 자막(`transcript_segment.text`)에서만 자른다


@dataclass(frozen=True)
class BlacklistRequestCreated:
    request: BlacklistRequest
    has_distress: bool  # 위기 신호가 섞였다 — 화면이 전문 기관 연결 안내를 띄울 근거. 저장되지 않는다
