# Requirement: C-6
"""C-6 콜 가드 프로바이더 — 탐지(`CallGuardPort`)와 기록(`CallGuardRecordPort`).

**탐지 스포크가 없으면 None 이다. 501 이 아니다.** 콜 가드는 전사 수신 경로에 **얹혀** 돈다 —
여기서 501 을 올리면 `ai/` 가 안 실린 배포에서 **자막·마스킹까지 멈춘다.** 빠진 것은
`/health` 의 `spokes` 에 `call_guard` 가 없는 것으로 밖에서 보인다(`decisions/024` 와 같은 방식).
「탐지 결과 없음」과 섞이지 않는 이유: 탐지가 없으면 `call_guard_flag` 에 **아무것도 쓰지 않는다** —
빈 목록으로 갈아끼우지 않는다(`TranscriptIngestInteractor` 참고).
"""

from __future__ import annotations

from fastapi import Request

from hub.adapter.outbound.log_call_guard_record_adapter import LogCallGuardRecordAdapter
from hub.adapter.outbound.postgres.call_guard_flag_repository import PostgresCallGuardFlagRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.output.call_guard_port import CallGuardPort
from hub.app.ports.output.call_guard_record_port import CallGuardRecordPort


def get_call_guard_port() -> CallGuardPort | None:
    """합성 루트(`server/main.py`)가 `ai/` 의 규칙 구현으로 덮는다."""
    return None


def get_call_guard_record_port(request: Request) -> CallGuardRecordPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        return LogCallGuardRecordAdapter()
    return PostgresCallGuardFlagRepository(build_connection_factory(settings))
