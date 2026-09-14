# Requirement: C-6
"""CallGuardPort 프로바이더. 스포크가 없으면 501 — 빈 목록을 돌려주지 않는다.

빈 목록은 "폭언이 없었다"로 읽힌다. 탐지기가 아예 없는 상태를 그렇게 보고하면 상담원 보호가 꺼진 것을
'조용한 통화'로 오해하게 만든다. 구현체는 합성 루트(`main.py`)가 `ai/` 에서 꽂는다.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from hub.app.ports.output.call_guard_port import CallGuardPort


def get_call_guard_port() -> CallGuardPort:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="call_guard 스포크가 등록되지 않았습니다 (C-6)",
    )
