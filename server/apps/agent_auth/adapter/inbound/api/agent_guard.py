# Requirement: J-1
"""상담원 전용 라우터가 재사용하는 인증 가드 (`decisions/307`). `Authorization: Bearer <cga_…>` 를 읽어
상담원 ID 를 돌려준다 — 없거나 폐기됐거나 형식이 다르면 401.

**요청 본문의 상담원 ID 를 믿지 않는다.** 전에는 `requested_by` 를 본문으로 받아 `agent` 에 있는 아무 ID 로나
요청할 수 있었다(`decisions/304` 의 남은 구멍). 이 가드를 단 라우터는 누가 요청했는지를 토큰에서만 얻는다.

헤더 검사를 저장소 의존성보다 먼저 한다 — 헤더가 없으면 DB 설정 여부(501)와 무관하게 401 이다
(관리자 가드와 같은 이유, 2026-09-15)."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from agent_auth.app.ports.input.current_agent_use_case import CurrentAgentUseCase
from agent_auth.dependencies.use_case_providers import get_current_agent_use_case


def agent_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="상담원 토큰이 필요합니다 — 관리자에게 받은 토큰으로 로그인해 주세요")
    return authorization.split(" ", 1)[1].strip()


async def require_agent(
    token: str = Depends(agent_bearer_token),  # ⚠ 순서가 계약이다 — use_case 보다 앞에 둔다
    use_case: CurrentAgentUseCase = Depends(get_current_agent_use_case),
) -> str:
    agent_id = await use_case.current(token)
    if agent_id is None:
        raise HTTPException(status_code=401, detail="상담원 토큰이 없거나 폐기됐습니다 — 관리자에게 새 토큰을 요청해 주세요")
    return agent_id
