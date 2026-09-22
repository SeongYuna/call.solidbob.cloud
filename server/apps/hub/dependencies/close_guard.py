# Requirement: SEC-1, D-1
"""`POST /hub/calls/{id}/close` 의 문 (`_project/decisions/315`).

부르는 쪽이 둘이다 — **대시보드**(상담원이 통화 후 처리를 연다 → 상담원 토큰)와 **합성 통화 재생기**
(`services/call-mediator/scripts/replay_persona_call.ts --close` → 서비스 토큰 `INGEST_SERVICE_TOKEN`).
그래서 둘 중 하나를 받는다. 전에는 **아무 토큰도 요구하지 않아** 주소를 아는 누구나 통화를 닫고 초안을 덮을 수 있었다.

⚠ 쓰기 일곱 경로(`ingest_guard`)와 달리 **서비스 토큰이 미설정이어도 열지 않는다** — 상담원 토큰 길이 늘 있다.
누가 닫았는지는 기록하지 않는다(초안은 사람 몫이 아니고, 확정은 `summary-confirmation` 이 따로 상담원을 받는다).
"""

from __future__ import annotations

from agent_auth.adapter.inbound.api.agent_guard import agent_bearer_token
from agent_auth.app.ports.input.current_agent_use_case import CurrentAgentUseCase
from agent_auth.dependencies.use_case_providers import get_current_agent_use_case
from fastapi import Depends, HTTPException, Request, status

from hub.dependencies.ingest_guard import service_token_matches


async def require_close_caller(
    request: Request,
    token: str = Depends(agent_bearer_token),  # ⚠ 순서가 계약이다 — 헤더 없으면 DB 전에 401
    agents: CurrentAgentUseCase = Depends(get_current_agent_use_case),
) -> None:
    if service_token_matches(getattr(request.app.state.settings, "ingest_service_token", None), token):
        return
    if await agents.current(token) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="상담원 토큰 또는 서비스 토큰이 필요하다 — 없거나 폐기됐다",
            headers={"WWW-Authenticate": "Bearer"},
        )
