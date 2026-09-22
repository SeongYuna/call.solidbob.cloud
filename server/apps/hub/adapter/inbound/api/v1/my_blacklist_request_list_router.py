# Requirement: J-2, J-4
"""GET /hub/blacklist-requests/mine — 상담원이 자기 요청과 결과(반려 사유 포함)를 본다(`w6-agent-my-requests-api`).

`decisions/316` 으로 반려 사유가 저장되지만 요청자가 볼 길이 없었다. **요청자는 상담원 토큰에서만 얻는다** — 쿼리·본문으로 남의 ID 를
받지 않으므로 남의 요청은 볼 수 없다. 관리자 목록(`GET /hub/blacklist-requests`)과 경로는 가깝지만 문이 다르다.
"""

from __future__ import annotations

from agent_auth.adapter.inbound.api.agent_guard import require_agent
from fastapi import APIRouter, Depends

from hub.adapter.inbound.api.schemas.my_blacklist_request_list_schema import (
    MyBlacklistRequestItemSchema,
    MyBlacklistRequestListResponse,
)
from hub.app.ports.input.my_blacklist_request_list_use_case import MyBlacklistRequestListUseCase
from hub.dependencies.my_blacklist_request_list_provider import get_my_blacklist_request_list_use_case

my_blacklist_request_list_router = APIRouter(prefix="/hub", tags=["hub"])


@my_blacklist_request_list_router.get("/blacklist-requests/mine", response_model=MyBlacklistRequestListResponse)
async def list_my_blacklist_requests(
    agent_id: str = Depends(require_agent),  # ⚠ 순서 — 헤더 없으면 DB 전에 401
    use_case: MyBlacklistRequestListUseCase = Depends(get_my_blacklist_request_list_use_case),
) -> MyBlacklistRequestListResponse:
    requests = await use_case.list(agent_id)
    return MyBlacklistRequestListResponse(requests=[MyBlacklistRequestItemSchema.from_dto(r) for r in requests])
