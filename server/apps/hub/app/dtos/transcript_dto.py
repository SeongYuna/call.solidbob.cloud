# Requirement: 7.3절 전사 이벤트, C-5, SEC-1
"""전사 이벤트 (마스킹 적용 후).

계약 v2 예시:
    {"call_id": "c_001", "segment_id": 17, "speaker": "customer",
     "text": "카드번호는 **** 입니다", "masked": [{"type": "P2", "span": [7, 11]}],
     "is_final": true, "utterance_end_ms": 3100}

이 객체가 존재한다는 것은 이미 마스킹을 거쳤다는 뜻이다. 마스킹 전 원문으로 이 객체를 만들면 안 된다 —
그 경계는 masking 스포크의 adapter/inbound 안이다 (docs/architecture.md §5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Speaker = Literal["customer", "agent"]


@dataclass(frozen=True)
class MaskedSpan:
    type: str  # P1~P7 (docs/domain.md §4.1)
    span: tuple[int, int]  # [start, end) — 마스킹 후 text 기준 문자 오프셋


@dataclass(frozen=True)
class TranscriptEvent:
    call_id: str
    segment_id: int  # interim 여러 건을 구분하는 식별자 (decisions/003 ④)
    speaker: Speaker
    text: str  # 마스킹 완료본만
    is_final: bool
    utterance_end_ms: int | None = None  # is_final 일 때만 의미 있음 — 트리거 채점 기준점
    masked: tuple[MaskedSpan, ...] = field(default_factory=tuple)
    # 게이트웨이가 STT 결과를 받은 시각 — utterance_end_ms 와 같은 통화 기준 ms. 실시간 경로만 채운다.
    # 트리거가 발동 시각으로 쓴다(없으면 모형값). 골든셋·배치에는 없다 (w4-trigger-arrival-time)
    received_at_ms: int | None = None
