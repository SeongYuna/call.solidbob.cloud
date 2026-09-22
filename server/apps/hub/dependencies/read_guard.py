# Requirement: SEC-1, SEC-2
"""읽기 경로의 문 — 통화 목록·전사·통화 기록·수동 검색(`_project/decisions/322`).

운영에서 `GET /hub/calls` 가 토큰 없이 실제 음성 테스트 통화·고객 HMAC 까지 보여 줬다. 부르는 쪽은 상담원 화면
(`apps/call` — 상담원 토큰이 이미 있다)과 합성 통화 검사(`e2e_check.py` — 서비스 토큰). **둘 다 아직 토큰을 싣지 않아**
`120` 처럼 두 단계로 닫는다:

1. 지금 — 토큰을 **받는다.** 실었는데 틀리면 401(프론트가 틀린 값을 싣는 것을 이행기에 찾는다). 안 실으면 지나간다
2. `READ_AUTH_REQUIRED=true` — 토큰 없는 요청도 401. 프론트가 싣기 시작한 뒤 켠다(코드 배포 없이 `server-env` 로)

열려 있는지는 `/health` 의 `read_guard` 가 말한다 — 조용한 열림을 만들지 않는다.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from agent_auth.dependencies.providers import get_agent_token_port
from agent_auth.dependencies.use_case_providers import get_current_agent_use_case
from fastapi import Depends, Header, HTTPException, Request, status

from hub.dependencies.ingest_guard import service_token_matches

AgentTokenChecker = Callable[[str], Awaitable[bool]]


def read_guard_state(settings: object) -> str:
    return "locked" if getattr(settings, "read_auth_required", False) else "open"


def get_agent_token_checker(request: Request) -> AgentTokenChecker:
    """상담원 토큰 확인을 **토큰이 왔을 때만** DB 로 한다 — 안 실은 요청은 이행기에 DB 설정 여부와 무관하게 지나가야 한다."""

    async def check(token: str) -> bool:
        use_case = get_current_agent_use_case(get_agent_token_port(request))  # DB 없으면 501
        return await use_case.current(token) is not None

    return check


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


async def require_reader(
    request: Request,
    authorization: str | None = Header(default=None),
    agent_ok: AgentTokenChecker = Depends(get_agent_token_checker),
) -> None:
    settings = request.app.state.settings
    scheme, _, token = (authorization or "").partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        if getattr(settings, "read_auth_required", False):
            raise _unauthorized("상담원 토큰 또는 서비스 토큰이 필요하다")
        return  # 이행기 — `READ_AUTH_REQUIRED` 를 켜면 닫힌다(/health read_guard)
    if service_token_matches(getattr(settings, "ingest_service_token", None), token):
        return
    if not await agent_ok(token):
        raise _unauthorized("토큰이 틀렸거나 폐기됐다")
