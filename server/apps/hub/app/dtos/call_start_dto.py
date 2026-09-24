# Requirement: 7.3절 전사 이벤트, SEC-1
"""통화 시작 — `call` 행을 만드는 명령과 결과.

`transcript_segment.call_id` 가 `call` 을 외래키로 참조하므로, 전사가 오기 전에 통화가 먼저
있어야 한다. 그 행을 만드는 경로가 없어서 첫 전사부터 저장이 실패했다(2026-09-10,
`_project/decisions/301`). 통화 시작은 콜 미디에이터가 알린다 — 전사 첫 건에서 `domain`·
`stt_engine` 을 지어내지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

# db/schema.sql `call.domain` CHECK 와 같다. 도메인은 다산 하나지만(decisions/201) DDL 이 아직 4종이다.
CallDomain = Literal["finance", "dasan", "shopping", "health"]


@dataclass(frozen=True)
class CallStartCommand:
    call_id: str
    domain: CallDomain
    stt_engine: str
    channel_count: int
    started_at: datetime | None = None  # 없으면 인터랙터가 지금 시각을 넣는다
    # ⚠ 평문 발신 번호(C-5 P4). 인터랙터가 곧바로 `CustomerRefPort` 로 바꾸고 버린다 — 저장·로그·응답에 싣지 않는다
    caller_phone: str | None = None


@dataclass(frozen=True)
class CallStarted:
    """저장된 통화. `created` 가 False 면 같은 `call_id` 가 이미 있어 그대로 두었다(멱등)."""

    call_id: str
    domain: CallDomain
    stt_engine: str
    channel_count: int
    started_at: datetime
    status: str
    created: bool
    customer_id: str | None = None  # 발신 번호의 HMAC. 번호가 없거나 키가 없으면 None — 지어내지 않는다
    # 이미 있던 통화(`created=False`)에 저장된 가장 큰 발화 번호. 새 통화면 0. 콜 미디에이터가 여기서 이어 센다
    last_segment_id: int = 0
